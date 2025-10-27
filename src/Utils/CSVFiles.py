import csv
import os

from sqlalchemy import update, insert

from Config import setup_logger
from Database.Models import Registrations
from .MicroUtils import to_bool

logger = setup_logger("csv_processor")


async def process_csv_file(session, csv_file: str):
    try:
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                stmt = (
                    update(Registrations)
                    .where(Registrations.reg == row["reg"])
                    .values(
                        reg=row["reg"],
                        msn=int(row["msn"]) if row["msn"] != "" else None,
                        aircraft_type=row["aircraft"],
                        indashboard=to_bool(row["indashboard"]),
                    )
                    .execution_options(synchronize_session="fetch")
                )
                result = await session.execute(stmt)

                if result.rowcount == 0:
                    await session.execute(
                        insert(Registrations).values(
                            reg=row["reg"],
                            msn=int(row["msn"]) if row["msn"] != "" else None,
                            aircraft_type=row["aircraft"],
                            indashboard=to_bool(row["indashboard"]),
                        )
                    )
        logger.info(f"[CSV] Processed {csv_file}")
    except Exception as e:
        logger.error(f"[CSV] Error processing {csv_file}: {e}")
    finally:
        if os.path.exists(csv_file):
            os.remove(csv_file)
            logger.debug(f"[CSV] Removed {csv_file}")


__all__ = ["process_csv_file"]
