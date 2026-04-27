from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid
import asyncio

app = FastAPI(title="FlightRadar Service")

jobs = {}

class StartRequest(BaseModel):
    id: Optional[str] = None
    reg: Optional[str] = None
    icao: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    type: Optional[str] = None

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

@app.post("/start", response_model=StartResponse)
async def start_extraction(params: StartRequest, background_tasks: BackgroundTasks):
    """Starts stub background job"""
    job_id = str(uuid.uuid4())
    
    jobs[job_id] = {
        "status": "running",
        "progress": 0,
        "params": params.dict(),
        "started_at": datetime.now().isoformat(),
        "last_update": None
    }
    
    background_tasks.add_task(stub_job, job_id)
    
    return StartResponse(
        job_id=job_id,
        status="started",
        message="Extraction job started (stub)"
    )

@app.post("/stop", response_model=StopResponse)
async def stop_extraction(job_id: str):
    """Stops the job"""
    if job_id not in jobs:
        return StopResponse(
            job_id=job_id,
            status="error",
            message="Job not found"
        )
    
    jobs[job_id]["status"] = "stopped"
    jobs[job_id]["last_update"] = datetime.now().isoformat()
    
    return StopResponse(
        job_id=job_id,
        status="stopped",
        message="Extraction job stopped"
    )

@app.get("/status", response_model=StatusResponse)
async def get_status(job_id: str):
    """Returns job status"""
    if job_id not in jobs:
        return StatusResponse(
            job_id=job_id,
            status="error",
            progress=0,
            last_update=None
        )
    
    job = jobs[job_id]
    return StatusResponse(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        last_update=job.get("last_update")
    )

async def stub_job(job_id: str):
    """Simulates data extraction: 10 steps, 2 seconds each"""
    for i in range(1, 11):
        
        if jobs[job_id]["status"] == "stopped":
            break
        
        jobs[job_id]["progress"] = i * 10
        jobs[job_id]["last_update"] = datetime.now().isoformat()
        
        await asyncio.sleep(2)
    
    if jobs[job_id]["status"] != "stopped":
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["last_update"] = datetime.now().isoformat()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
