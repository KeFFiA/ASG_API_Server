from pydantic import BaseModel
from typing import Optional, List

class CountrySchema(BaseModel):
    code: str
    name: str

class TimezoneSchema(BaseModel):
    name: str
    offset: int

class SurfaceSchema(BaseModel):
    type: str
    description: str

class RunwaySchema(BaseModel):
    designator: str
    heading: int
    length: int
    width: int
    elevation: int
    thr_coordinates: Optional[List[float]] = None
    surface: SurfaceSchema

class AirportResponseSchema(BaseModel):
    name: str
    iata: Optional[str] = None
    icao: Optional[str] = None
    lon: float
    lat: float
    elevation: int
    city: str
    state: Optional[str] = None
    country: CountrySchema
    timezone: TimezoneSchema
    runways: List[RunwaySchema] = []
