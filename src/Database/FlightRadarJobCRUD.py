from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from src.Database.FlightRadarJobModel import FlightRadarJob
import uuid


async def create_job(db: AsyncSession, params: dict) -> FlightRadarJob:
    """Create new job in database"""
    job = FlightRadarJob(
        status="running",
        progress=0,
        params=params
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


async def update_job(db: AsyncSession, job_id: uuid.UUID, **kwargs) -> None:
    """Update job fields (status, progress, error_message, etc.)"""
    await db.execute(
        update(FlightRadarJob)
        .where(FlightRadarJob.id == job_id)
        .values(**kwargs)
    )
    await db.commit()
