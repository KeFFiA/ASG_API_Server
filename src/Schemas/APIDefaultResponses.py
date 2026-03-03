import inspect
import sys
from typing import Optional

from fastapi import status

from pydantic import BaseModel, Field
from uuid import UUID


class BaseResponse(BaseModel):
    correlationId: UUID = Field(..., title="", description="Operation ID")


class DetailField(BaseResponse):
    msg: str = Field(..., title="", description="Detail message")


class DefaultResponse(BaseModel):
    status_code: int = Field(..., title="", description="Response status code")
    details: DetailField = Field(..., title="", description="Response details")
    data: Optional[dict | list] = Field(default=None, title="", description="Response data")


class ErrorValidObject(DetailField):
    field: str = Field(..., title="", description="Field name")


class ErrorValidationResponse(BaseModel):
    details: list[ErrorValidObject] = Field(..., title="", description="Error details")
    status_code: int = Field(default=status.HTTP_422_UNPROCESSABLE_ENTITY, title="", description="Error status code")


_current_module = sys.modules[__name__]

__all__ = [
    name
    for name, obj in globals().items()
    if inspect.isclass(obj) and obj.__module__ == __name__
]

