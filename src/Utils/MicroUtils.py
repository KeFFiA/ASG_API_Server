import inspect
import os
import sys
from pathlib import Path
from fastapi import Request, BackgroundTasks, status
from fastapi.responses import FileResponse
from pydantic import ValidationError

from Config import RESPONSES_PATH, FILES_PATH
from Schemas import ErrorValidationResponse, ErrorValidObject


def to_bool(value: str) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("true", "1", "yes", "y", "t")


def remove_file(path: str | Path):
    try:
        os.remove(path)
    except FileNotFoundError:
        raise FileNotFoundError(f"File {path} not found")
    except Exception:
        os.remove(str(path))


async def validation_error_file(request: Request, exc: ValidationError, filename: str, background_tasks: BackgroundTasks) -> FileResponse:
    detail = [
        ErrorValidObject(field=".".join(map(str, e["loc"])), description=e["msg"])
        for e in exc.errors()
    ]
    filepath = Path(RESPONSES_PATH / filename)
    error_response = ErrorValidationResponse(
        correlationId=request.state.correlation_id,
        detail=detail
    )
    filepath.write_text(error_response.model_dump_json(indent=4), encoding="utf-8")
    background_tasks.add_task(remove_file, str(filepath))
    background_tasks.add_task(remove_file, str(Path(FILES_PATH / filename)))
    return FileResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        path=filepath,
        filename=filename,
        media_type="application/json",
        background=background_tasks
    )


_current_module = sys.modules[__name__]

__all__ = [
    name
    for name, obj in globals().items()
    if (inspect.isfunction(obj) or inspect.isasyncgenfunction(obj)) and obj.__module__ == __name__
]
