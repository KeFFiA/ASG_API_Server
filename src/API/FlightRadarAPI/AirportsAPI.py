import logging
import asyncio
from typing import Iterable, Optional

import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession

from Config import FLIGHT_RADAR_URL, FLIGHT_RADAR_HEADERS
from Database import DatabaseClient
from src.Services.AirportService import airport_exists, save_airport
from src.Schemas.AirportSchemas import AirportResponseSchema

logger = logging.getLogger(__name__)


async def fetch_airport(
    session: aiohttp.ClientSession,
    code: str,
    retries: int = 3,
    timeout: int = 30
) -> Optional[AirportResponseSchema]:
    """Fetch airport data from FlightRadar API with retries and timeout"""
    url = f"{FLIGHT_RADAR_URL}/static/airports/{code}/full"
    
    for attempt in range(retries):
        try:
            timeout_obj = aiohttp.ClientTimeout(total=timeout)
            async with session.get(url, headers=FLIGHT_RADAR_HEADERS, timeout=timeout_obj) as resp:
                logger.info(f"Fetching airport {code}, status={resp.status}, attempt={attempt+1}")
                
                if resp.status == 200:
                    data = await resp.json()
                    return AirportResponseSchema(**data)
                elif resp.status == 404:
                    logger.warning(f"Airport {code} not found")
                    return None
                else:
                    logger.warning(f"Airport {code} returned status {resp.status}")
                    
        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching airport {code}, attempt={attempt+1}")
        except aiohttp.ClientError as e:
            logger.warning(f"Client error fetching airport {code}: {e}, attempt={attempt+1}")
        except Exception as e:
            logger.error(f"Unexpected error fetching airport {code}: {e}, attempt={attempt+1}")
        
        if attempt < retries - 1:
            await asyncio.sleep(2 ** attempt)  # exponential backoff
    
    logger.error(f"Failed to fetch airport {code} after {retries} attempts")
    return None


async def load_airports(codes: Iterable[str]) -> None:
    """Load airports from API and save to database"""
    client = DatabaseClient()
    async with aiohttp.ClientSession() as http:
        async with client.session("flightradar") as session:
            for code in codes:
                logger.info(f"Processing airport code: {code}")
                data = await fetch_airport(http, code)
                if not data:
                    logger.warning(f"No data for airport {code}")
                    continue

                exists = await airport_exists(
                    session,
                    iata=data.iata,
                    icao=data.icao,
                )
                if exists:
                    logger.info(f"Airport {code} already exists, skipping")
                    continue

                await save_airport(session, data)
                logger.info(f"Airport {code} saved successfully")

            await session.commit()
            logger.info("All airports processed and committed")


if __name__ == "__main__":
    airport_codes = [
        "UASB", "UAUR", "LLKS", "OEPS", "YSPK", "YTHY"
    ]
    
    asyncio.run(load_airports(airport_codes))
