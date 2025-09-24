import asyncio
import glob
import os
import csv

from Config import FILES_PATH, setup_logger
from sqlalchemy import update, insert
from ..Database import Registrations

logger = setup_logger("csv_loader")


async def process_csv_file(csv_file: str, session):
    try:
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            async with session.begin():
                for row in reader:
                    stmt = (
                        update(Registrations)
                        .where(Registrations.reg == row["reg"])
                        .values(
                            reg=row["reg"],
                            msn=row["msn"],
                            indashboard=row["indashboard"],
                        )
                        .execution_options(synchronize_session="fetch")
                    )
                    result = await session.execute(stmt)

                    if result.rowcount == 0:
                        await session.execute(
                            insert(Registrations).values(
                                reg=row["reg"],
                                msn=row["msn"],
                                indashboard=row["indashboard"],
                            )
                        )
        logger.info(f"✅ Processed {csv_file}")
    except Exception as e:
        logger.error(f"❌ Error processing {csv_file}: {e}")
    finally:
        os.remove(csv_file)
        logger.debug(f"Removed {csv_file}")


async def find_csv_loop(client):
    while True:
        csv_files = sorted(
            glob.glob(os.path.join(FILES_PATH, "*.csv")),
            key=os.path.getmtime
        )

        if csv_files:
            logger.info(f"Found {len(csv_files)} CSV files")
            async with client.session("main") as session:
                for csv_file in csv_files:
                    await process_csv_file(csv_file, session)

        logger.debug("Waiting for new files...")
        await asyncio.sleep(5)

