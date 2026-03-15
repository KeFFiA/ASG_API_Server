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


class AircraftsAdditionalQuery(BaseModel):
    aircraft_id: int = Query(..., description="Aircraft ID")


class CreateAircraftQuery(BaseModel):
    aircraft_id: Optional[int] = Query(default=None, description="Aircraft ID")
    template_id: int = Query(..., description="Template ID")
    airline_id: int = Query(..., description="Airline ID")
    aircraft_registration: str = Query(..., description="Aircraft registration number")
    aircraft_msn: int = Query(..., description="Aircraft MSN")
    in_dashboard: bool = Query(default=True, description="Is In Dashboard")
    status: str = Query(default="Insured", description="Status")
    policy_from: Optional[date] = Query(default=None, description="Policy from")
    policy_to: Optional[date] = Query(default=None, description="Policy to")

    engines_manufacture: Optional[str] = Query(default=None, description="Engines manufacture")
    engines_model: Optional[str] = Query(default=None, description="Engines model")
    number_of_engines: Optional[int] = Query(default=None, description="Number of engines")
    engine1_msn: Optional[int] = Query(default=None, description="Engine1 MSN")
    engine2_msn: Optional[int] = Query(default=None, description="Engine2 MSN")
    engine3_msn: Optional[int] = Query(default=None, description="Engine3 MSN")
    engine4_msn: Optional[int] = Query(default=None, description="Engine4 MSN")
    agreed_value: Optional[float] = Query(default=None, description="Agreed value")
    agreed_value_down_absolute: Optional[float] = Query(default=None, description="Agreed value down absolute")
    agreed_value_down_percent: Optional[float] = Query(default=None, description="Agreed value down percent")
    combined_single_limit: Optional[float] = Query(default=None, description="Combined single limit")
    all_risks_deductible: Optional[float] = Query(default=None, description="All risks deductible")
    hull_and_spares_excess: Optional[float] = Query(default=None, description="Hull and spares excess")

    lessee: Optional[str] = Query(default=None, description="Lessee")
    lessor: Optional[str] = Query(default=None, description="Lessor")




class ClaimsQuery(BaseModel):
    claim_id: Optional[int] = Query(default=None, description="Claim ID")
    user_id: Optional[UUID] = Query(default=None, description="User ID")


class ClaimsDeleteQuery(BaseModel):
    claim_id: int = Query(..., description="Claim ID")

