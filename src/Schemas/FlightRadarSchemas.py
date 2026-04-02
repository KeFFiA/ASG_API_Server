import inspect
import sys
from datetime import datetime
from typing import Optional, List

from fastapi import Query
from pydantic import BaseModel, Field, model_validator


class RequestFRFlightSummary(BaseModel):
    regs: Optional[str] = Query(default=None)
    airlines: Optional[str] = Query(default=None)
    start_date: datetime = Query()
    end_date: datetime = Query()
    user: Optional[str] = Query(default=None)

    @model_validator(mode="after")
    def validate_dates(self):
        if self.start_date >= self.end_date:
            raise ValueError(
                "start_date must be earlier than end_date and cannot be equal"
            )
        return self




_current_module = sys.modules[__name__]

__all__ = [
    name
    for name, obj in globals().items()
    if inspect.isclass(obj) and obj.__module__ == __name__
]
