import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import select, insert, String, Float, Date, Boolean

from Config import setup_logger
from Database.Models import AircraftRevision, CiriumAircrafts


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


def bool_value(val: str | int | float | None) -> bool | None:
    if val is None or (isinstance(val, float) and pd.isna(val)) or pd.isna(val):
        return None

    if isinstance(val, bool):
        return val

    if isinstance(val, (int, float)):
        if val == 1:
            return True
        if val == 0:
            return False
        return None

    val_str = str(val).strip().lower()
    if val_str in TRUE_VALUES:
        return True
    if val_str in FALSE_VALUES:
        return False
    return None


async def get_or_create_today_revision(session) -> AircraftRevision:
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


async def process_cirium_file(session, file: str):
    file_path = Path(file)
    if not file_path.exists():
        raise FileNotFoundError(f"[Cirium] Excel file not found: {file}")

    try:
        df = pd.read_excel(file_path)
        rev = await get_or_create_today_revision(session)

        df = normalize_columns(df)

        df["revision_id"] = rev.id

        mapper = CiriumAircrafts.__mapper__
        orm_to_db = {attr.key: attr.columns[0].name for attr in mapper.column_attrs}
        df = df.rename(columns={v: k for k, v in orm_to_db.items()})

        df = df.copy()

        records = df.to_dict(orient="records")
        if records:
            row: AircraftRevision = await session.get(AircraftRevision, rev.id)
            row.data_rows_count += len(records)
            await session.execute(insert(CiriumAircrafts), records)
            await session.commit()

        logger.info(f"[Cirium] Processed file {file_path.name}, rows: {len(records)}. Revision: {rev.revision_number}")

    except Exception as e:
        logger.error(f"[Cirium] Processing file {file_path.name} failed: {e}")
        raise
    finally:
        if file_path.exists():
            file_path.unlink()
            logger.debug(f"[Cirium] Removed {file_path.name}")
