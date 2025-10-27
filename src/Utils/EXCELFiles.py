import asyncio
import os

import pandas as pd
from sqlalchemy import create_engine

from API.DremioAPI import transfer_tables_to_dremio
from Config import setup_logger, DBSettings

logger = setup_logger(name="excel_processor")

async def process_excel_file(session, excel_file: str):
    global xls, sync_engine
    db_settings = DBSettings()
    tables = []
    try:
        xls = pd.ExcelFile(excel_file)
        logger.info(f"[XLSX] File loaded. Sheets count: {len(xls.sheet_names)}")

        async_engine = session.get_bind()
        sync_db_url = str(async_engine.url).replace("+asyncpg", "+psycopg2").replace("***", db_settings.DB_PASSWORD)
        sync_engine = create_engine(sync_db_url)
        for sheet_name in xls.sheet_names:
            if sheet_name.upper() == "README":
                logger.info("[XLSX] Readme file skipped")
                continue
            df = pd.read_excel(xls, sheet_name=sheet_name)

            logger.debug(f"[XLSX] Row count: {len(df)}")

            df.columns = [c.strip() for c in df.columns]
            df.to_sql(sheet_name.lower(), sync_engine, if_exists="replace", index=False)

            tables.append(sheet_name.lower())
            logger.info(f"[XLSX] Sheet '{sheet_name}' saved to DB with name: {sheet_name.lower()}")

        asyncio.create_task(transfer_tables_to_dremio(tables=tables, dremio_space="Superset", dremio_source_name="Main"))
    except Exception as _ex:
        logger.error(f"[XLSX] Error processing: {_ex}")

    finally:
        try:
            sync_engine.dispose()
            xls.close()
        except Exception:
            pass
        if os.path.exists(excel_file):
            os.remove(excel_file)
            logger.debug(f"[XLSX] Removed {excel_file.split('\\')[-1]}")
