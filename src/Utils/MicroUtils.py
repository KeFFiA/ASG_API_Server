import csv
from datetime import datetime, timezone, timedelta
import inspect
import os
import sys
from pathlib import Path
from typing import List, Optional

import numpy as np
from fastapi import Request, BackgroundTasks, status
from fastapi.responses import FileResponse
from pydantic import ValidationError
from sqlalchemy import Integer, Float, String, DateTime

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


def pandas_to_python_type(dtype):
    if isinstance(dtype, np.dtype):
        if np.issubdtype(dtype, np.integer):
            return int
        if np.issubdtype(dtype, np.floating):
            return float
        if np.issubdtype(dtype, np.bool_):
            return bool
        if np.issubdtype(dtype, np.datetime64):
            return datetime

        return str

    dtype_str = str(dtype)

    if "string" in dtype_str:
        return str
    if "Int" in dtype_str:
        return int
    if "Float" in dtype_str:
        return float
    if "boolean" in dtype_str:
        return bool

    return str


def sqlalchemy_to_python_type(sql_type):
    if isinstance(sql_type, Integer):
        return int
    elif isinstance(sql_type, Float):
        return float
    elif isinstance(sql_type, String):
        return str
    elif isinstance(sql_type, DateTime):
        import datetime
        return datetime.datetime
    else:
        return object


def next_quarter(dt: datetime) -> datetime:
    dt = dt.replace(second=0, microsecond=0)
    minutes = ((dt.minute // 15) + 1) * 15
    if minutes == 60:
        return dt.replace(minute=0) + timedelta(hours=1)
    return dt.replace(minute=minutes)


def write_csv(rows: List[dict], path: str):
    file_exists = Path(path).exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt.astimezone(timezone.utc)


def parse_date_or_datetime(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def ensure_naive_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def get_today_range_utc() -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)

    return (
        start_of_day.strftime("%Y-%m-%d %H:%M:%S"),
        now.strftime("%Y-%m-%d %H:%M:%S"),
    )


def get_earliest_time(flights: List[dict]) -> Optional[str]:
    times = []
    for flight in flights:
        if flight["first_seen"]:
            try:
                dt = datetime.strptime(flight["first_seen"], "%Y-%m-%d %H:%M:%S")
                times.append(dt)
            except ValueError:
                pass
    if times:
        return min(times).strftime("%Y-%m-%d %H:%M:%S")
    return None


_current_module = sys.modules[__name__]

__all__ = [
    name
    for name, obj in globals().items()
    if (inspect.isfunction(obj) or inspect.isasyncgenfunction(obj)) and obj.__module__ == __name__
]
