import inspect
import sys
from typing import List, Optional
from fastapi import status

from pydantic import BaseModel, Field
from uuid import UUID


class DetailField(BaseModel):
    msg: str = Field(..., title="")


class BaseResponse(BaseModel):
    correlationId: UUID = Field(..., title="", description="Operation ID")


class ErrorResponse(BaseResponse):
    detail: List[DetailField] = Field(..., title="", description="Error description")
    code: int = Field(..., title="", description="Error status code")


class SuccessResponse(BaseResponse):
    detail: List[DetailField] = Field(..., title="", description="Response details")
    code: int = Field(..., title="", description="Response status code")


class WarningResponse(BaseResponse):
    detail: List[DetailField] = Field(..., title="", description="Warning description")
    code: int = Field(..., title="", description="Warning status code")


class ErrorValidObject(BaseModel):
    field: str = Field(..., title="", description="Field name")
    description: str = Field(..., title="", description="Error description")


class ErrorValidationResponse(BaseResponse):
    detail: List[ErrorValidObject] = Field(..., title="", description="Error details")
    code: int = Field(default=status.HTTP_422_UNPROCESSABLE_ENTITY, title="", description="Error status code")


class SuccessDataResponse(SuccessResponse):
    data: List[dict] = Field(..., title="", description="Success data")


_current_module = sys.modules[__name__]

__all__ = [
    name
    for name, obj in globals().items()
    if inspect.isclass(obj) and obj.__module__ == __name__
]

