import json
import os

from pydantic import ValidationError

from Config import setup_logger
from Schemas import JsonFileSchema
from .Queueing import add_to_queue

logger = setup_logger("json_processor")


async def process_json_file(session, json_file):
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            file_data = json.load(f)
        validated = JsonFileSchema(**file_data)

        for filename in validated.filename.split(','):
            await add_to_queue(
                filename=filename.strip(),
                user_email=validated.user_email,
                _type=validated.type,
                session=session
            )
            await session.commit()
        logger.info(f"[JSON] Added {file_data['filename']} in queue")
    except json.JSONDecodeError as _ex:
        logger.error(f"[JSON] File error: {json_file} - {_ex}")
    except ValidationError as _ex:
        logger.error(f"[JSON] File structure error: {json_file} - {_ex} \n\n Expected: {JsonFileSchema.model_json_schema()}")
    finally:
        if os.path.exists(json_file):
            os.remove(json_file)
            logger.debug(f"[JSON] Removed {json_file}")


__all__ = ["process_json_file"]
