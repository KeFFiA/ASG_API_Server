import inspect
import sys
from typing import List, Optional

from pydantic import BaseModel, Field
from uuid import UUID


class BaseResponse(BaseModel):
    correlationId: UUID = Field(..., title="", description="Operation ID.")


class ErrorResponse(BaseResponse):
    description: str = Field(..., title="", description="Error description")
    code: str = Field(..., title="", description="Error code.")


class SuccessResponse(BaseResponse):
    detail: str = Field(..., title="", description="Response details.")


class WarningResponse(BaseResponse):
    description: str = Field(..., title="", description="Warning description.")
    code: str = Field(..., title="", description="Warning code.")


_current_module = sys.modules[__name__]

__all__ = [
    name
    for name, obj in globals().items()
    if inspect.isclass(obj) and obj.__module__ == __name__
]

