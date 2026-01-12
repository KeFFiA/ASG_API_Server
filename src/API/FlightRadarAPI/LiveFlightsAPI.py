from datetime import datetime, timezone
from typing import List, Optional

import aiohttp
from sqlalchemy import select

from Config import FLIGHT_RADAR_HEADERS, \
    FLIGHT_RADAR_MAX_REG_PER_BATCH, FLIGHT_RADAR_URL
from Database import LivePositions, DatabaseClient, Registrations
from Utils import get_today_range_utc, get_earliest_time, ensure_naive_utc, parse_dt, write_csv, performance_timer
from .FlightSummary import fetch_all_ranges, logger


_last_flights: Optional[List[dict]] = None
_last_run_date: datetime | None = None


@performance_timer
async def live_flights(storage_mode: str = "db",
                       csv_path: Optional[str] = None, regs: Optional[List[str]] = None):
    global _last_flights, _last_run_date

    logger.info("[Live Flights] Starting query")

    client: DatabaseClient = DatabaseClient()
    now = datetime.now(timezone.utc)

    first_run = (_last_run_date != now)
    _last_run_date = now

    if regs is None:
        async with client.session("main") as session:
            stmt = (
                select(
                    Registrations.reg
                )
                .where(Registrations.indashboard == True)
            )
            result = await session.execute(stmt)
            regs = result.scalars().all()

    if first_run:
        start_date, end_date = get_today_range_utc()
    else:
        earliest = get_earliest_time(_last_flights)
        if earliest:
            start_date = earliest
        else:
            # Fallback
            start_date, end_date = get_today_range_utc()
        _, end_date = get_today_range_utc()

    flights_nested = await fetch_all_ranges(registrations=regs, start_date=start_date, end_date=end_date,
                                            storage_mode=storage_mode)
    _last_flights = flights_nested

    flight_ids = list({
        flight.get("flight")
        for group in flights_nested if group is not None
        for flight in group if flight.get("flight")
    })

    flight_id_batches = (
        [flight_ids[i:i + FLIGHT_RADAR_MAX_REG_PER_BATCH] for i in
         range(0, len(flight_ids), FLIGHT_RADAR_MAX_REG_PER_BATCH)]
        if flight_ids else [None]
    )

    for batch_index, flight_batch in enumerate(flight_id_batches):
        if flight_batch:
            logger.debug(f"\n[Live Flights] Processing a batch of flights {batch_index + 1} out of {len(flight_id_batches)}")
        params = {
            "flights": ",".join(flight_batch),
            "limit": 20000
        }
        async with client.session("flightradar") as session:
            async with aiohttp.ClientSession() as http:
                async with http.get(f"{FLIGHT_RADAR_URL}/live/flight-positions/full", headers=FLIGHT_RADAR_HEADERS,
                                    params=params) as resp:
                    try:
                        if resp.status != 200:
                            logger.error(f"{resp.status}: {await resp.text()}")
                            break

                        flights = await resp.json()
                        if not flights or not flights.get("data"):
                            logger.debug("[Live Flights] No data for the current interval.")
                            break

                        flights_data = flights["data"]
                        if not flights_data:
                            break

                        flights = []
                        csv_rows = []

                        for flight in flights_data:
                            row_data = {
                                "fr24_id": flight.get("fr24_id"),
                                "flight": flight.get("flight"),
                                "callsign": flight.get("callsign"),
                                "lat": flight.get("lat"),
                                "lon": flight.get("lon"),
                                "track": flight.get("track"),
                                "alt": flight.get("alt"),
                                "gspeed": flight.get("gspeed"),
                                "vspeed": flight.get("vspeed"),
                                "squawk": flight.get("squawk"),
                                "timestamp": ensure_naive_utc(parse_dt(flight.get("timestamp"))),
                                "source": flight.get("source"),
                                "hex": flight.get("hex"),
                                "type": flight.get("type"),
                                "reg": flight.get("reg"),
                                "painted_as": flight.get("painted_as"),
                                "operating_as": flight.get("operating_as"),
                                "orig_iata": flight.get("orig_iata"),
                                "orig_icao": flight.get("orig_icao"),
                                "dest_iata": flight.get("dest_iata"),
                                "dest_icao": flight.get("dest_icao"),
                                "eta": ensure_naive_utc(parse_dt(flight.get("eta")))
                            }

                            if storage_mode in ("db", "both"):
                                flights.append(LivePositions(**row_data))
                            if storage_mode in ("csv", "both"):
                                csv_rows.append(row_data)

                    except Exception as e:
                        logger.warning(f"[Live Flights] Record processing error: {e}")

                    if flights and storage_mode in ("db", "both"):
                        session.add_all(flights)
                        await session.commit()
                        logger.debug(f"[Live Flights] Saved {len(flights)} new records to DB.")

                    if csv_rows and storage_mode in ("csv", "both") and csv_path:
                        write_csv(csv_rows, csv_path)
                        logger.debug(f"[Live Flights] Appended {len(csv_rows)} records to CSV.")

    logger.info("Query completed")

