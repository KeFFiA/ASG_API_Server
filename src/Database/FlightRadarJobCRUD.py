from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from src.Database.FlightRadarJobModel import FlightRadarJob
import uuid
from datetime import datetime

async def create_job(db: AsyncSession, params: dict) -> FlightRadarJob:
    """Create new job in database"""
    job = FlightRadarJob(
        status="running",
        progress=0,
        params=params,
        created_at=datetime.utcnow()
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job

async def get_job(db: AsyncSession, job_id: uuid.UUID) -> FlightRadarJob | None:
    """Get job by id"""
    result = await db.execute(
        select(FlightRadarJob).where(FlightRadarJob.id == job_id)
    )
    return result.scalar_one_or_none()

async def update_job_status(db: AsyncSession, job_id: uuid.UUID, status: str) -> None:
    """Update job status"""
    await db.execute(
        update(FlightRadarJob)
        .where(FlightRadarJob.id == job_id)
        .values(status=status, updated_at=datetime.utcnow())
    )
    await db.commit()

async def update_job_progress(db: AsyncSession, job_id: uuid.UUID, progress: int) -> None:
    """Update job progress"""
    await db.execute(
        update(FlightRadarJob)
        .where(FlightRadarJob.id == job_id)
        .values(progress=progress, updated_at=datetime.utcnow())
    )
    await db.commit()
