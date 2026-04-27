from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class StartRequest(BaseModel):
    id: Optional[str] = Field(None, description="Flight ID")
    reg: Optional[str] = Field(None, description="Registration number")
    icao: Optional[str] = Field(None, description="ICAO24 address")
    start_date: Optional[datetime] = Field(None, description="Start date")
    end_date: Optional[datetime] = Field(None, description="End date")
    type: Optional[str] = Field(None, description="Flight type")
    
    def model_post_init(self, __context):
        if not any([self.id, self.reg, self.icao]):
            raise ValueError("At least one of 'id', 'reg', or 'icao' must be provided")

class StartResponse(BaseModel):
    job_id: str
    status: str
    message: str

class StopResponse(BaseModel):
    job_id: str
    status: str
    message: str

class StatusResponse(BaseModel):
    job_id: str
    status: str
    progress: int
    last_update: Optional[str] = None

