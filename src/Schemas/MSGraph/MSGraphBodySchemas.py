from datetime import date
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ApplicationFileLoadBody(BaseModel):
    file_name: str = Field(..., description="File name")
    file_description: Optional[str] = Field(default=None, description="File description")
    file_data: str = Field(..., description="File data")


class CreateAirlinesBody(BaseModel):
    file_data: Optional[str] = Field(None, description="File data")
    airline_name: str = Field(..., description="Airline name")
    airline_icao: str = Field(..., description="Airline ICAO")
    user_id: Optional[UUID] = Field(default=None, description="User ID")


class CreateAircraftTemplatesBody(BaseModel):
    file_data: Optional[str] = Field(None, description="File data")
    template_name: str = Field(..., description="Template name")


class CreateClaimSchema(BaseModel):
    claim_id: Optional[int] = Field(default=None, description="Claim ID")
    user_id: UUID = Field(..., description="User ID")
    aircraft_id: int = Field(..., description="Aircraft ID")
    date_of_loss: Optional[date] = Field(default=None, description="Date of loss")
    location_of_loss: Optional[str] = Field(default=None, description="Location of loss")
    status: str = Field(..., description="Status")
    damage: Optional[str] = Field(default=None, description="Damage")
    indemnity_reserve_amount: Optional[float] = Field(default=None, description="Indemnity reserve amount")
    paid_to_date_amount: Optional[float] = Field(default=None, description="Paid to date amount")
    paid_date: Optional[date] = Field(default=None, description="Paid date")
    is_hd: Optional[bool] = Field(default=False, description="Is Hull Deductible")
    is_hw: Optional[bool] = Field(default=False, description="Is Hull War")
    is_hsl: Optional[bool] = Field(default=False, description="Is HSL")
    leader: Optional[str] = Field(default=None, description="Leader")
    surveyor: Optional[str] = Field(default=None, description="Surveyor")



