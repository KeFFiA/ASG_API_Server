import datetime
import io
from pathlib import Path

import pandas as pd
from asyncpg import PostgresError
from sqlalchemy import select, insert, String, Float, Date, Boolean

from Config import setup_logger
from Database.Models import AircraftRevision, CiriumAircrafts
from Utils import performance_timer

logger = setup_logger("cirium_processor")

skip_cols = {"revision_id", "id", "created_at", "updated_at"}

db_columns = {col for col in CiriumAircrafts.__table__.columns}

STR_COLS = {
    "Aircraft Minor Variant", "Series", "Current Family", "Fleet Number", "Master Series", "Type", "Serial Number",
    "Manufacturer",
    "Registration", "Status", "Operator", "Manager", "Owner", "Engine Type"
}
DB_STR_COLS = {col.name for col in db_columns if isinstance(col.type, String)}

FLOAT_COLS = {
    "Business Class Primary IFE Screen Size (in)", "Business Class Seat Recline (in)",
    "Economy Class Primary IFE Screen Size (in)", "Economy Class Seat Width (in)", "Status Duration (years)",
    "Economy Class Seat Recline (in)", "Business Class Seat Pitch (in)", "Business Class Seat Width (in)",
    "Economy Class Seat Pitch (in)", "Economy Class Seat Recline (deg)"
}
DB_FLOAT_COLS = {col.name for col in db_columns if isinstance(col.type, Float)}

DATE_COLS = {
    "Lease Start", "Lease End", "Reported Hours and Cycles Date", "Operator Delivery Date", "Order Date",
    "In Service Date", "Delivery Date", "First Flight Date", "Status Change Date"
}
DB_DATE_COLS = {col.name for col in db_columns if isinstance(col.type, Date)}

DB_BOOL_COLS = {col.name for col in db_columns if isinstance(col.type, Boolean)}

TRUE_VALUES = {"y", "yes", "true"}
FALSE_VALUES = {"n", "no", "false"}

# TODO: ^^^^ MOVE TO CONFIG ^^^^

def bool_value(val: str | int | float | None) -> bool | None:
    if val is None or (isinstance(val, float) and pd.isna(val)) or pd.isna(val):
        return None

    if isinstance(val, bool):
        return val

    if isinstance(val, (int, float)):
        if int(val) == 1:
            return True
        if int(val) == 0:
            return False
        return None

    val_str = str(val).strip().lower()
    if val_str in TRUE_VALUES:
        return True
    if val_str in FALSE_VALUES:
        return False
    return None


@performance_timer
async def get_or_create_revision(session) -> AircraftRevision:
    today = datetime.date.today()
    last_rev = await session.scalar(
        select(AircraftRevision).order_by(AircraftRevision.revision_number.desc()).limit(1)
    )

    if not last_rev or last_rev.created_at.date() != today:
        new_rev = AircraftRevision(
            revision_number=1 if not last_rev else last_rev.revision_number + 1,
            created_at=datetime.datetime.now()
        )
        session.add(new_rev)
        await session.flush()
        logger.debug(f"Created revision: {new_rev.revision_number}")
        return new_rev

    logger.debug(f"Using previous revision: {last_rev.revision_number}")
    return last_rev


@performance_timer
def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = df.columns.str.strip()

    for col in df.columns:
        if col in STR_COLS or col in DB_STR_COLS:
            df[col] = df[col].apply(lambda x: pd.NA if pd.isna(x) else str(x))
        elif col in FLOAT_COLS or col in DB_FLOAT_COLS:
            df[col] = df[col].apply(lambda x: pd.NA if pd.isna(x) else float(x))
        elif col in DATE_COLS or col in DB_DATE_COLS:
            df[col] = pd.to_datetime(df[col], errors='coerce').apply(
                lambda x: pd.NA if pd.isna(x) else x.date()
            )
        elif col in DB_BOOL_COLS:
            try:
                df[col] = df[col].apply(lambda x: pd.NA if pd.isna(x) else bool_value(x)).astype('boolean')
            except Exception:
                df[col] = df[col].apply(lambda x: pd.NA if pd.isna(x) else x).astype('boolean')
        else:
            series = df[col]
            try:
                df[col] = series.apply(lambda x: pd.NA if pd.isna(x) else int(x)).astype('Int64')
            except Exception:
                try:
                    df[col] = series.apply(lambda x: pd.NA if pd.isna(x) else float(x))
                except Exception:
                    try:
                        df[col] = series.apply(lambda x: pd.NA if pd.isna(x) else bool_value(x)).astype('boolean')
                    except Exception:
                        try:
                            df[col] = series.apply(lambda x: pd.NA if pd.isna(x) else str(x))
                        except Exception:
                            try:
                                df[col] = pd.to_datetime(series, errors='coerce').apply(
                                    lambda x: pd.NA if pd.isna(x) else x.date()
                                )
                            except Exception:
                                df[col] = series.apply(lambda x: pd.NA if pd.isna(x) else x)
    return df


def df_to_csv_buffer(df: pd.DataFrame) -> io.BytesIO:
    buffer = io.BytesIO()
    df.to_csv(buffer, index=False, header=False, encoding="utf-8")
    buffer.seek(0)
    return buffer


@performance_timer
async def bulk_insert_df(
        session,
        table_name: str,
        filename: str,
        df: pd.DataFrame,
        chunk_fallback: int = 3000,
):
    conn = await session.connection()
    raw = await conn.get_raw_connection()
    pgconn = raw.driver_connection

    mapper = CiriumAircrafts.__mapper__
    orm_to_db = {attr.key: attr.columns[0].name for attr in mapper.column_attrs}
    df = df.rename(columns={k: v for k, v in orm_to_db.items()})

    buffer = df_to_csv_buffer(df)
    columns = list(df.columns)

    try:
        await pgconn.copy_to_table(
            table_name,
            source=buffer,
            columns=columns,
            format="csv"
        )

        await session.commit()
        return len(df)

    except PostgresError as _ex:
        logger.debug(f"Processing file {filename} failed: {_ex}")

        # fallback
        records = df.to_dict(orient="records")
        chunk = chunk_fallback

        for i in range(0, len(records), chunk):
            batch = records[i:i + chunk]
            await session.execute(
                insert(CiriumAircrafts),
                batch
            )

        await session.commit()
        return len(records)


@performance_timer
async def process_cirium_file(session, file: str):
    file_path = Path(file)
    if not file_path.exists():
        raise FileNotFoundError(f"Excel file not found: {file}")
    logger.info(f"Processing file {file_path.name}")

    try:
        rev = await get_or_create_revision(session)

        df = pd.read_excel(file_path)
        df = normalize_columns(df)
        df = df.assign(revision_id=rev.id)

        row: AircraftRevision = await session.get(AircraftRevision, rev.id)
        len_rows = await bulk_insert_df(
            session=session,
            table_name="ciriumaircraft",
            df=df,
            filename=file_path.name
        )
        row.data_rows_count += len_rows

        logger.info(f"Processed file {file_path.name}, rows: {len_rows}. Revision: {rev.revision_number}")

    except Exception as _ex:
        logger.error(f"Processing file {file_path.name} failed: {_ex}")
    finally:
        if file_path.exists():
            file_path.unlink()
            logger.debug(f"Removed {file_path.name}")
