from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid

from Services.FlightRadarService import fr_test

router = APIRouter(prefix="/flightradar", tags=["FlightRadar"])

jobs = {}

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
    params: StartRequest

class StopResponse(BaseModel):
    job_id: str
    status: str
    message: str

class StatusResponse(BaseModel):
    job_id: str
    status: str
    progress: int
    last_update: Optional[str] = None

@router.post("/start", response_model=StartResponse)
async def start_extraction(params: StartRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    
    jobs[job_id] = {
        "status": "running",
        "progress": 0,
        "params": params.dict(),
        "started_at": datetime.now().isoformat()
    }
    
    background_tasks.add_task(run_job, job_id)
    
    return StartResponse(
        job_id=job_id,
        status="started",
        message="Extraction job started",
        params=params
    )

@router.post("/stop")
async def stop_extraction(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    jobs[job_id]["status"] = "stopped"
    
    return StopResponse(
        job_id=job_id,
        status="stopped",
        message="Extraction job stopped"
    )

@router.get("/status")
async def get_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    return StatusResponse(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        last_update=job.get("last_update")
    )

async def run_job(job_id: str):
    import asyncio
    
    for i in range(1, 11):
        if jobs[job_id]["status"] == "stopped":
            break
        
        jobs[job_id]["progress"] = i * 10
        jobs[job_id]["last_update"] = datetime.now().isoformat()
        
        await fr_test()
        await asyncio.sleep(1)
    
    if jobs[job_id]["status"] != "stopped":
        jobs[job_id]["status"] = "completed"
