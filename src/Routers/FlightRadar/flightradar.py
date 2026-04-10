from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import httpx

router = APIRouter(prefix="/flightradar", tags=["FlightRadar"])

FLIGHTRADAR_URL = "http://localhost:8001"

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

@router.post("/start")
async def start_extraction(params: StartRequest):
    
    request_data = params.dict()
    if request_data.get("start_date"):
        request_data["start_date"] = request_data["start_date"].isoformat()
    if request_data.get("end_date"):
        request_data["end_date"] = request_data["end_date"].isoformat()
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{FLIGHTRADAR_URL}/start",
            json=request_data
        )
        return response.json()

@router.post("/stop")
async def stop_extraction(job_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{FLIGHTRADAR_URL}/stop",
            params={"job_id": job_id}
        )
        return response.json()

@router.get("/status")
async def get_status(job_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{FLIGHTRADAR_URL}/status",
            params={"job_id": job_id}
        )
        return response.json()
