import asyncio
import glob
import json
import os

from Config import FILES_PATH, setup_logger
from pydantic import ValidationError

from Database import DatabaseClient, PDF_Queue
from Schemas import JsonFileSchema

logger = setup_logger("json_processor")


async def find_json_loop():
    client = DatabaseClient()
    while True:
        json_files = sorted(
            glob.glob(os.path.join(FILES_PATH, "*.json")),
            key=os.path.getmtime
        )
        if len(json_files) > 0:
            logger.info(f"Found {len(json_files)} json files")
            async with client.session("service") as session:
                for json_file in json_files:
                    try:
                        with open(json_file, "r", encoding="utf-8") as f:
                            file_data = json.load(f)
                        validated = JsonFileSchema(**file_data)
                    except (json.JSONDecodeError, ValidationError) as e:
                        logger.error(f"Invalid JSON: {json_file.split("\\")[-1]} - {e}")
                        os.remove(json_file)
                        logger.debug(f"Removed {json_file.split("\\")[-1]}")
                        continue
                    os.remove(json_file)
                    logger.debug(f"Removed {json_file.split("\\")[-1]}")

                    for filename in validated.filename.split(','):
                        session.add(PDF_Queue(
                            filename=filename.strip(),
                            user_email=validated.user_email,
                            type=validated.type
                        ))

                        logger.info(f"Added {file_data['filename']} in queue")

        logger.debug("Waiting for new files")
        await asyncio.sleep(5)
