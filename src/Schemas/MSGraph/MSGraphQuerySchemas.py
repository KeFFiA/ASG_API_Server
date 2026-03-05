from datetime import date
from typing import Optional, List
from uuid import UUID

from fastapi import Query
from pydantic import BaseModel, EmailStr


class GetUserSchemaQuery(BaseModel):
    user_email: EmailStr = Query(description="Email of the user")


class ApplicationIdQuery(BaseModel):
    application_id: Optional[UUID] = Query(default=None, description="Application ID")


class ApplicationSizeQuery(BaseModel):
    screen_size: Optional[int] = Query(default=None, description="Screen size")


class ApplicationFileQuery(BaseModel):
    file_name: Optional[str] = Query(None, description="File name")
    file_id: Optional[int] = Query(None, description="File ID")


class AirlinesQuery(BaseModel):
    airline_name: Optional[str] = Query(default=None, description="Airline name")
    airline_id: Optional[int] = Query(default=None, description="Airline ID")
    user_id: Optional[UUID] = Query(default=None, description="User ID")


class AircraftTemplatesQuery(BaseModel):
    template_name: Optional[str] = Query(default=None, description="Template name")
    template_id: Optional[int] = Query(default=None, description="Template ID")


class AircraftsQuery(BaseModel):
    aircraft_id: Optional[int] = Query(default=None, description="Aircraft ID")
    aircraft_registration: Optional[str] = Query(default=None, description="Aircraft registration number")
    aircraft_msn: Optional[int] = Query(default=None, description="Aircraft MSN")
    template_name: Optional[str] = Query(default=None, description="Template name")
    template_id: Optional[int] = Query(default=None, description="Template ID")
    airline_name: Optional[str] = Query(default=None, description="Airline name")
    airline_id: Optional[int] = Query(default=None, description="Airline ID")


class CreateAircraftQuery(BaseModel):
    template_id: int = Query(..., description="Template ID")
    airline_id: int = Query(..., description="Airline ID")
    aircraft_registration: str = Query(..., description="Aircraft registration number")
    aircraft_msn: int = Query(..., description="Aircraft MSN")
    policy_from: Optional[date] = Query(default=None, description="Policy from")
    policy_to: Optional[date] = Query(default=None, description="Policy to")
    hulldeductible_franchise: float = Query(default=0.0, description="Hull deductible franchise")
    threshold: float = Query(default=0.0, description="Threshold")
    in_dashboard: bool = Query(default=True, description="Is In Dashboard")
    status: str = Query(default="Insured", description="Status")

