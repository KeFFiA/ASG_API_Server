import inspect
import sys
from datetime import date, timedelta, datetime
from typing import List, Optional
from uuid import UUID

from fastapi import Query
from pydantic import BaseModel, EmailStr, HttpUrl, Field

from ..Enums.MSGraphAPI import UserTypesEnum


class InviteUserSchemaQuery(BaseModel):
    user_email: EmailStr = Query(description="Email of the user")
    user_displayName: Optional[str] = Query(None, description="Display name of the user", examples=["Marco Polo"])
    user_type: UserTypesEnum = Query(UserTypesEnum.GUEST, description="Type of the user",
                                     examples=[UserTypesEnum.GUEST, UserTypesEnum.MEMBER])
    inviter_email: EmailStr = Query(description="Email of the inviter")
    custom_message: Optional[str] = Query(None, description="Custom message in user invitation")
    expires_at: Optional[date] = Query(default_factory=lambda: date.today() + timedelta(days=30),
                                       description="Expiration date in YYYY-MM-DD format")
    reset_redemption: bool = Query(False, description="Reset redemption")
    redirect_url: Optional[HttpUrl] = Query("https://myaccount.microsoft.com/organizations",
                                            description="Redirect URL after accepting invitation. Only HTTPS allowed")


class InviteUserSchema(BaseModel):
    user_email: EmailStr = Field(description="Email of the user")
    user_displayName: Optional[str] = Field(None, description="Display name of the user", examples=["Marco Polo"])
    user_type: UserTypesEnum = Field(UserTypesEnum.GUEST, description="Type of the user",
                                     examples=[UserTypesEnum.GUEST, UserTypesEnum.MEMBER])
    inviter_email: EmailStr = Field(description="Email of the inviter")
    custom_message: Optional[str] = Field(None, description="Custom message in user invitation")
    expires_at: Optional[date] = Field(default_factory=lambda: date.today() + timedelta(days=30),
                                       description="Expiration date in YYYY-MM-DD format")
    reset_redemption: bool = Field(False, title="", description="Reset redemption")
    redirect_url: Optional[HttpUrl] = Field("https://myaccount.microsoft.com/organizations",
                                            description="Redirect URL after accepting invitation. Only HTTPS allowed")


class RulesSchema(BaseModel):
    rule_id: int
    rule_name: str
    rule_description: Optional[str]


class ApplicationAccessResponseSchema(BaseModel):
    application_id: UUID
    rules: List[RulesSchema]
    main_access: bool
    super_admin: bool


class UserSchema(BaseModel):
    user_id: UUID
    display_name: Optional[str]
    given_name: Optional[str]
    surname: Optional[str]
    user_principal_name: Optional[str]
    account_enabled: Optional[bool]
    mail: Optional[str]
    mobile_phone: Optional[str]
    city: Optional[str]
    country: Optional[str]
    department: Optional[str]
    job_title: Optional[str]
    employee_id: Optional[str]
    employee_hire_date: Optional[date]
    created_date_time: Optional[datetime]
    manager_id: Optional[UUID]
    application_accesses: List[ApplicationAccessResponseSchema]


class GetUserAccessResponseSchema(BaseModel):
    user_id: UUID
    applications: List[ApplicationAccessResponseSchema]

    class Config:
        from_attributes = True


class GetRuleResponseSchema(BaseModel):
    application_id: UUID
    rules: List[RulesSchema]


class GetRulesResponseSchema(BaseModel):
    application: List[GetRuleResponseSchema]


class FontsSchema(BaseModel):
    font_name: str
    font_size: int
    font_color: str
    font_weight: str
    screen_size: int
    usage_name: str


class GetFontsResponseSchema(BaseModel):
    font: List[FontsSchema]


class GetFileResponseSchema(BaseModel):
    file_name: Optional[str]
    file_description: Optional[str]
    file_data: Optional[str]


class UserSchemaShort(BaseModel):
    user_id: UUID
    user_displayname: str
    user_mail: EmailStr | str


class AirlineSchema(BaseModel):
    airline_id: int
    airline_name: str
    airline_icao: str
    asset: GetFileResponseSchema


class AirlinesSchemaUsers(AirlineSchema):
    users: List[UserSchemaShort]


class AirlinesSchemaByUser(BaseModel):
    user: UserSchemaShort
    airlines: List[AirlineSchema]


class AircraftTemplateSchema(BaseModel):
    template_id: int
    template_name: str
    asset: GetFileResponseSchema


class AircraftSchema(BaseModel):
    aircraft_id: int
    registration: str
    msn: int
    policy_from: Optional[date]
    policy_to: Optional[date]
    hulldeductible_franchise: float
    threshold: float
    in_dashboard: bool
    status: str
    airline: AirlineSchema
    template: AircraftTemplateSchema


class GetClaimSchema(BaseModel):
    claim_id: int
    users: List[UserSchemaShort]
    aircraft: AircraftSchema
    date_of_loss: Optional[date]
    location_of_loss: Optional[str]
    status: Optional[str]
    damage: Optional[str]
    indemnity_reserve_amount: Optional[float]
    paid_to_date_amount: Optional[float]
    paid_date: Optional[date]
    is_hd: Optional[bool]
    is_hw: Optional[bool]
    is_hsl: Optional[bool]
    leader: Optional[str]
    surveyor: Optional[str]




_current_module = sys.modules[__name__]

__all__ = [
    name
    for name, obj in globals().items()
    if inspect.isclass(obj) and obj.__module__ == __name__
]
