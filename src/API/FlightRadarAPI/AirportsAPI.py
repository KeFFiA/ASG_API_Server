from typing import Iterable, Optional

import aiohttp
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from Config import FLIGHT_RADAR_URL, FLIGHT_RADAR_HEADERS
from Database import DatabaseClient
from Database.Models import Airport, AirportRunway


async def fetch_airport(
        session: aiohttp.ClientSession,
        code: str,
) -> Optional[dict]:
    async with session.get(f"{FLIGHT_RADAR_URL}/static/airports/{code}/full", headers=FLIGHT_RADAR_HEADERS) as resp:
        print(resp.status, await resp.json())
        if resp.status != 200:
            return None
        return await resp.json()


async def airport_exists(
        session: AsyncSession,
        iata: Optional[str],
        icao: Optional[str],
) -> bool:
    stmt = select(Airport.id)

    if icao and iata:
        stmt = stmt.where(
            (Airport.icao == icao) | (Airport.iata == iata)
        )
    elif icao:
        stmt = stmt.where(Airport.icao == icao)
    elif iata:
        stmt = stmt.where(Airport.iata == iata)
    else:
        return False

    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def save_airport(session: AsyncSession, data: dict) -> None:
    country = data.get("country")
    timezone = data.get("timezone")
    airport = Airport(
        name=data.get("name"),
        iata=data.get("iata"),
        icao=data.get("icao"),
        lon=data.get("lon"),
        lat=data.get("lat"),
        elevation=data.get("elevation"),
        city=data.get("city"),
        state=data.get("state"),
        country_code=country.get("code"),
        country_name=country.get("name"),
        timezone_name=timezone.get("name"),
        timezone_offset=timezone.get("offset"),
    )

    for rw in data.get("runways", []):
        thr = rw.get("thr_coordinates") or []
        if len(thr) != 2:
            thr_lat = 0.0
            thr_lon = 0.0
        else:
            thr_lat = thr[0]
            thr_lon = thr[1]

        surface = rw.get("surface")
        airport.runways.append(
            AirportRunway(
                designator=rw.get("designator"),
                heading=rw.get("heading"),
                length=rw.get("length"),
                width=rw.get("width"),
                elevation=rw.get("elevation"),
                thr_lat=thr_lat,
                thr_lon=thr_lon,
                surface_type=surface.get("type"),
                surface_description=surface.get("description"),
            )
        )

    session.add(airport)


async def load_airports(codes: Iterable[str]) -> None:
    client = DatabaseClient()
    async with aiohttp.ClientSession() as http:
        async with client.session("flightradar") as session:
            for code in codes:
                print(code)
                data = await fetch_airport(http, code)
                if not data:
                    print("No data")
                    continue

                exists = await airport_exists(
                    session,
                    iata=data.get("iata"),
                    icao=data.get("icao"),
                )
                if exists:
                    print("Exists")
                    continue

                await save_airport(session, data)
                print("Saved")

            await session.commit()


if __name__ == "__main__":
    import asyncio

    airport_codes = [
        "UASB", "UAUR", "LLKS", "OEPS", "YSPK", "YTHY"
    ]

    asyncio.run(load_airports(airport_codes))
