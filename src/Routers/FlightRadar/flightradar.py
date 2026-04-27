from fastapi import APIRouter, Depends, BackgroundTasks
import uuid
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.Database.database import get_db
from src.Database.FlightRadarJobCRUD import create_job, get_job, update_job
from src.Schemas.FlightRadar import StartRequest

router = APIRouter(prefix="/flightradar", tags=["FlightRadar"])


async def run_stub_job(job_id: uuid.UUID, db: AsyncSession):
    """Background stub job that simulates work and updates progress in database"""
    for i in range(1, 11):
        await asyncio.sleep(2)
        progress = i * 10
        await update_job(db, job_id, progress=progress)

    await update_job(db, job_id, status="completed")


@router.post("/start", status_code=201)
async def start_extraction(
    params: StartRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Start extraction - creates job in database and runs background stub"""
    job = await create_job(db, params.dict())
    background_tasks.add_task(run_stub_job, job.id, db)

    return {
        "job_id": str(job.id),
        "status": job.status,
        "message": "Extraction job started (stub)"
    }


@router.post("/stop")
async def stop_extraction(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Stop extraction - updates job status in database"""
    job_uuid = uuid.UUID(job_id)
    job = await get_job(db, job_uuid)

    if not job:
        return {
            "job_id": job_id,
            "status": "error",
            "message": "Job not found"
        }

    await update_job(db, job_uuid, status="stopped")

    return {
        "job_id": job_id,
        "status": "stopped",
        "message": "Extraction job stopped"
    }


@router.get("/status")
async def get_status(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get status - reads from database"""
    job_uuid = uuid.UUID(job_id)
    job = await get_job(db, job_uuid)

    if not job:
        return {
            "job_id": job_id,
            "status": "error",
            "progress": 0,
            "last_update": None
        }

    return {
        "job_id": str(job.id),
        "status": job.status,
        "progress": job.progress,
        "last_update": job.updated_at.isoformat() if job.updated_at else None
    }
