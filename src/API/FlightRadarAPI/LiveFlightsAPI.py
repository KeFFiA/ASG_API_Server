import json
import time
from datetime import datetime, timezone
from typing import List, Optional, Set

import aiohttp
from redis.asyncio import Redis

from Config import FLIGHT_RADAR_HEADERS, \
    FLIGHT_RADAR_MAX_REG_PER_BATCH, FLIGHT_RADAR_URL, FLIGHT_RADAR_REDIS_POLLING_KEY, FLIGHT_RADAR_REDIS_META_KEY, \
    FLIGHT_RADAR_CHECK_INTERVAL_MISS, FLIGHT_RADAR_CHECK_INTERVAL_FOUND, FLIGHT_RADAR_REDIS_TTL_SECONDS, DBSettings
from Database import LivePositions, DatabaseClient
from Utils import ensure_naive_utc, parse_dt, performance_timer

try:
    from .FlightSummary import logger
except:
    from API.FlightRadarAPI.FlightSummary import logger

_last_flights: Optional[List[dict]] = None
_last_run_date: datetime | None = None


class FlightPollingStorage:
    def __init__(self, username: str, password: str, host: str, port: int):
        self.redis = Redis(username=username, password=password, host=host, port=port, decode_responses=True)

    async def init_regs(self, regs: list[str]):
        now = time.time()

        regs = [r for r in regs if r]
        if not regs:
            return

        mapping = {reg: now for reg in regs}

        await self.redis.zadd(FLIGHT_RADAR_REDIS_POLLING_KEY, mapping)

        await self.redis.expire(FLIGHT_RADAR_REDIS_POLLING_KEY, FLIGHT_RADAR_REDIS_TTL_SECONDS)
        await self.redis.expire(FLIGHT_RADAR_REDIS_META_KEY, FLIGHT_RADAR_REDIS_TTL_SECONDS)

    async def get_regs_to_check(self, limit: int = 1000) -> list[str]:
        """
        Atomically fetch and remove ready registrations
        """
        now = time.time()

        regs = await self.redis.zrangebyscore(
            FLIGHT_RADAR_REDIS_POLLING_KEY, min=0, max=now, start=0, num=limit
        )
        if not regs:
            return []

        await self.redis.zrem(FLIGHT_RADAR_REDIS_POLLING_KEY, *regs)
        return regs

    async def update_reg(self, reg: str, found: bool):
        now = time.time()

        next_check = now + (
            FLIGHT_RADAR_CHECK_INTERVAL_FOUND if found
            else FLIGHT_RADAR_CHECK_INTERVAL_MISS
        )

        await self.redis.zadd(
            FLIGHT_RADAR_REDIS_POLLING_KEY,
            {reg: next_check}
        )

        meta = {
            "state": "airborne" if found else "ground",
            "last_seen": datetime.now(timezone.utc).isoformat() if found else None,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        await self.redis.hset(FLIGHT_RADAR_REDIS_META_KEY, reg, json.dumps(meta))

        await self.redis.expire(FLIGHT_RADAR_REDIS_POLLING_KEY, FLIGHT_RADAR_REDIS_TTL_SECONDS)
        await self.redis.expire(FLIGHT_RADAR_REDIS_META_KEY, FLIGHT_RADAR_REDIS_TTL_SECONDS)


@performance_timer
async def live_flights_adaptive(
        storage_mode: str = "db"
):
    logger.info("[Live Flights] Adaptive polling started")
    username, password, host, port = DBSettings().get_reddis_credentials()

    redis_storage = FlightPollingStorage(username, password, host, port)
    db_client = DatabaseClient()

    regs_to_check = await redis_storage.get_regs_to_check()

    if not regs_to_check:
        logger.info("[Live Flights] Nothing to check — skipping API call")
        return

    logger.info(f"[Live Flights] Checking {len(regs_to_check)} aircrafts")

    batches = [
        regs_to_check[i:i + FLIGHT_RADAR_MAX_REG_PER_BATCH]
        for i in range(0, len(regs_to_check), FLIGHT_RADAR_MAX_REG_PER_BATCH)
    ]

    found_regs: Set[str] = set()

    async with aiohttp.ClientSession() as http:
        for batch in batches:
            params = {
                "registrations": ",".join(batch),
                "limit": 20000
            }

            async with http.get(
                    f"{FLIGHT_RADAR_URL}/live/flight-positions/full",
                    headers=FLIGHT_RADAR_HEADERS,
                    params=params
            ) as resp:

                if resp.status != 200:
                    logger.error(f"{resp.status}: {await resp.text()}")
                    continue

                payload = await resp.json()
                flights_data = payload.get("data", [])

                if not flights_data:
                    continue

                found_regs.update(
                    flight.get("reg") for flight in flights_data if flight.get("reg")
                )

                if storage_mode in ("db", "both"):
                    records = [
                        LivePositions(
                            fr24_id=f.get("fr24_id"),
                            flight=f.get("flight"),
                            callsign=f.get("callsign"),
                            lat=f.get("lat"),
                            lon=f.get("lon"),
                            track=f.get("track"),
                            alt=f.get("alt"),
                            gspeed=f.get("gspeed"),
                            vspeed=f.get("vspeed"),
                            squawk=f.get("squawk"),
                            timestamp=ensure_naive_utc(parse_dt(f.get("timestamp"))),
                            source=f.get("source"),
                            hex=f.get("hex"),
                            type=f.get("type"),
                            reg=f.get("reg"),
                            painted_as=f.get("painted_as"),
                            operating_as=f.get("operating_as"),
                            orig_iata=f.get("orig_iata"),
                            orig_icao=f.get("orig_icao"),
                            dest_iata=f.get("dest_iata"),
                            dest_icao=f.get("dest_icao"),
                            eta=ensure_naive_utc(parse_dt(f.get("eta")))
                        )
                        for f in flights_data
                    ]

                    async with db_client.session("flightradar") as session:
                        session.add_all(records)
                        await session.commit()

    for reg in regs_to_check:
        await redis_storage.update_reg(
            reg=reg,
            found=reg in found_regs
        )

    logger.info(
        f"[Live Flights] Completed. Active: {len(found_regs)}, inactive: {len(regs_to_check) - len(found_regs)}"
    )

