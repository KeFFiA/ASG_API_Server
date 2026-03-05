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
