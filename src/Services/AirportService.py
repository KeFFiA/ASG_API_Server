import logging
from typing import Iterable, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.Database.FlightRadarModels import Airport, AirportRunway
from src.Schemas.AirportSchemas import AirportResponseSchema

logger = logging.getLogger(__name__)


async def get_airport_by_code(
    db: AsyncSession,
    iata: Optional[str] = None,
    icao: Optional[str] = None
) -> Optional[Airport]:
    """Get airport by IATA or ICAO code"""
    if not iata and not icao:
        return None
    
    stmt = select(Airport)
    if icao:
        stmt = stmt.where(Airport.icao == icao)
    if iata:
        stmt = stmt.where(Airport.iata == iata)
    
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def airport_exists(
    db: AsyncSession,
    iata: Optional[str] = None,
    icao: Optional[str] = None
) -> bool:
    """Check if airport exists in database"""
    airport = await get_airport_by_code(db, iata, icao)
    return airport is not None


async def save_airport(
    db: AsyncSession,
    data: AirportResponseSchema
) -> Airport:
    """Save airport and runways to database"""
    country = data.country
    timezone = data.timezone
    
    airport = Airport(
        name=data.name,
        iata=data.iata,
        icao=data.icao,
        lon=data.lon,
        lat=data.lat,
        elevation=data.elevation,
        city=data.city,
        state=data.state,
        country_code=country.code,
        country_name=country.name,
        timezone_name=timezone.name,
        timezone_offset=timezone.offset,
    )
    
    for rw in data.runways:
        thr_lat, thr_lon = 0.0, 0.0
        if rw.thr_coordinates and len(rw.thr_coordinates) >= 2:
            thr_lat = rw.thr_coordinates[0]
            thr_lon = rw.thr_coordinates[1]
        
        airport.runways.append(
            AirportRunway(
                designator=rw.designator,
                heading=rw.heading,
                length=rw.length,
                width=rw.width,
                elevation=rw.elevation,
                thr_lat=thr_lat,
                thr_lon=thr_lon,
                surface_type=rw.surface.type,
                surface_description=rw.surface.description,
            )
        )
    
    db.add(airport)
    await db.commit()
    await db.refresh(airport)
    return airport
