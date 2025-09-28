import inspect
import sys
from datetime import date
from typing import List, Optional

from fastapi import Path
from pydantic import BaseModel, Field, EmailStr, HttpUrl
from .Enums.MSGraphAPI import UserTypesEnum


class InviteUserSchema(BaseModel):
    user_email: EmailStr = Field(description="Email of the user")
    user_displayName: Optional[str] = Field(None, description="Display name of the user", examples=["Marco Polo"])
    user_type: Optional[UserTypesEnum] = Field(UserTypesEnum.GUEST.value, description="Type of the user", examples=[UserTypesEnum.GUEST.value, UserTypesEnum.MEMBER.value])
    inviter_email: EmailStr = Field(description="Email of the inviter")
    custom_message: Optional[str] = Field(None, description="Custom message in user invitation")
    expires_at: Optional[date] = Field(None, description="Expiration date in YYYY-MM-DD format")
    redirect_url: Optional[HttpUrl] = Field(None, description="Redirect URL after accepting invitation")


class InviteUserFromFileSchema(BaseModel):
    filename: str = Path(description="Optional file name in '{FILES_PATH}'")



_current_module = sys.modules[__name__]

__all__ = [
    name
    for name, obj in globals().items()
    if inspect.isclass(obj) and obj.__module__ == __name__
]
