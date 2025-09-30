import inspect
import sys
from datetime import date, timedelta
from typing import List, Optional

from fastapi import Query
from pydantic import BaseModel, EmailStr, HttpUrl, Field

from .Enums.MSGraphAPI import UserTypesEnum


class InviteUserSchemaQuery(BaseModel):
    user_email: EmailStr = Query(description="Email of the user")
    user_displayName: Optional[str] = Query(None, description="Display name of the user", examples=["Marco Polo"])
    user_type: UserTypesEnum = Query(UserTypesEnum.GUEST, description="Type of the user", examples=[UserTypesEnum.GUEST, UserTypesEnum.MEMBER])
    inviter_email: EmailStr = Query(description="Email of the inviter")
    custom_message: Optional[str] = Query(None, description="Custom message in user invitation")
    expires_at: Optional[date] = Query(default_factory=lambda: date.today() + timedelta(days=30), description="Expiration date in YYYY-MM-DD format")
    reset_redemption: bool = Query(False, description="Reset redemption")
    redirect_url: Optional[HttpUrl] = Query("https://myaccount.microsoft.com/organizations", description="Redirect URL after accepting invitation. Only HTTPS allowed")


class InviteUserSchema(BaseModel):
    user_email: EmailStr = Field(description="Email of the user")
    user_displayName: Optional[str] = Field(None, description="Display name of the user", examples=["Marco Polo"])
    user_type: UserTypesEnum = Field(UserTypesEnum.GUEST, description="Type of the user", examples=[UserTypesEnum.GUEST, UserTypesEnum.MEMBER])
    inviter_email: EmailStr = Field(description="Email of the inviter")
    custom_message: Optional[str] = Field(None, description="Custom message in user invitation")
    expires_at: Optional[date] = Field(default_factory=lambda: date.today() + timedelta(days=30), description="Expiration date in YYYY-MM-DD format")
    reset_redemption: bool = Field(False, title="", description="Reset redemption")
    redirect_url: Optional[HttpUrl] = Field("https://myaccount.microsoft.com/organizations", description="Redirect URL after accepting invitation. Only HTTPS allowed")


_current_module = sys.modules[__name__]

__all__ = [
    name
    for name, obj in globals().items()
    if inspect.isclass(obj) and obj.__module__ == __name__
]
