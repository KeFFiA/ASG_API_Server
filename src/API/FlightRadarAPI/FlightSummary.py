import asyncio
from datetime import datetime, timedelta
from typing import Optional, List

import aiohttp
from sqlalchemy import select

from Config import setup_logger, FLIGHT_RADAR_HEADERS, FLIGHT_RADAR_SECONDS_BETWEEN_REQUESTS, \
    FLIGHT_RADAR_MAX_REG_PER_BATCH, FLIGHT_RADAR_RANGE_DAYS, FLIGHT_RADAR_URL, FLIGHT_RADAR_PATH
from Database import DatabaseClient
from Database.Models import FlightSummary, Registrations
from Utils import parse_dt, ensure_naive_utc, write_csv, parse_date_or_datetime, performance_timer

logger = setup_logger("flightradar")


async def fetch_date_range(
        icao: Optional[str],
        regs: Optional[List[str]],
        range_from: datetime,
        range_to: datetime,
        http: aiohttp.ClientSession,
        storage_mode: str = "db",
        csv_path: Optional[str] = None
) -> List[dict] | None:
    client: DatabaseClient = DatabaseClient()

    logger.debug("[Flight Summary] Starting query Fetch Date Range")

    if icao is not None:
        _icao = icao.upper()
    else:
        _icao = icao
    async with client.session("flightradar") as session:
        logger.debug(f"[Flight Summary] Range Processing: {range_from} - {range_to} | ICAO={_icao} | REGS={regs}")
        next_from = range_from

        processing_flights: List[dict] = []
        while True:
            params = {
                "flight_datetime_from": next_from.strftime("%Y-%m-%d %H:%M:%S"),
                "flight_datetime_to": range_to.strftime("%Y-%m-%d %H:%M:%S"),
                "limit": 20000
            }
            if icao:
                params["painted_as"] = _icao
            if regs:
                params["registrations"] = ",".join(regs)

            await asyncio.sleep(FLIGHT_RADAR_SECONDS_BETWEEN_REQUESTS)

            async with http.get(f"{FLIGHT_RADAR_URL}/flight-summary/full", headers=FLIGHT_RADAR_HEADERS,
                                params=params) as resp:
                if resp.status != 200:
                    logger.error(f"{resp.status}: {await resp.text()}")
                    break

                flights = await resp.json()
                if not flights or not flights.get("data"):
                    logger.debug("[Flight Summary] No data for the current interval.")
                    break

                flights_data = flights["data"]
                if not flights_data:
                    break

                existing_ids = set()
                if storage_mode in ("db", "both"):
                    stmt = select(
                        FlightSummary.fr24_id,
                        FlightSummary.flight,
                        FlightSummary.reg,
                        FlightSummary.callsign
                    ).where(
                        FlightSummary.fr24_id.in_([f.get("fr24_id") for f in flights_data if f.get("fr24_id")])
                    )

                    existing_rows = (await session.execute(stmt)).all()
                    existing_ids = {
                        (row[0], row[1], row[2], row[3])
                        for row in existing_rows
                    }

                new_flights = []
                csv_rows = []
                max_takeoff = next_from

                for flight in flights_data:
                    try:
                        fr24_id = flight.get("fr24_id")
                        flight_num = flight.get("flight")
                        reg = flight.get("reg")
                        callsign = flight.get("callsign")

                        if not fr24_id or ((fr24_id, flight_num, reg, callsign) in existing_ids and storage_mode in (
                                "db", "both")):
                            logger.debug(f"[Flight Summary] Skipping duplicate: {flight_num} ({reg}/{callsign})")
                            continue

                        takeoff = parse_dt(flight.get("datetime_takeoff"))
                        max_takeoff = max(max_takeoff, takeoff) if takeoff else max_takeoff

                        row_data = {
                            "fr24_id": fr24_id,
                            "flight": flight_num,
                            "callsign": callsign,
                            "operating_as": flight.get("operating_as"),
                            "painted_as": flight.get("painted_as"),
                            "type": flight.get("type"),
                            "reg": reg,
                            "orig_icao": flight.get("orig_icao"),
                            "orig_iata": flight.get("orig_iata"),
                            "datetime_takeoff": ensure_naive_utc(takeoff),
                            "runway_takeoff": flight.get("runway_takeoff"),
                            "dest_icao": flight.get("dest_icao"),
                            "dest_iata": flight.get("dest_iata"),
                            "dest_icao_actual": flight.get("dest_icao_actual"),
                            "dest_iata_actual": flight.get("dest_iata_actual"),
                            "datetime_landed": ensure_naive_utc(parse_dt(flight.get("datetime_landed"))),
                            "runway_landed": flight.get("runway_landed"),
                            "flight_time": flight.get("flight_time"),
                            "actual_distance": flight.get("actual_distance"),
                            "circle_distance": flight.get("circle_distance"),
                            "category": flight.get("category"),
                            "hex": flight.get("hex"),
                            "first_seen": ensure_naive_utc(parse_dt(flight.get("first_seen"))),
                            "last_seen": ensure_naive_utc(parse_dt(flight.get("last_seen"))),
                            "flight_ended": flight.get("flight_ended"),
                        }

                        if row_data["flight_ended"] is False:
                            processing_flights.append(row_data)

                        if row_data["flight_ended"] is True:
                            if storage_mode in ("db", "both"):
                                new_flights.append(FlightSummary(**row_data))
                            if storage_mode in ("csv", "both"):
                                csv_rows.append(row_data)

                    except Exception as e:
                        logger.warning(f"[Flight Summary] Record processing error: {e}")

                if new_flights and storage_mode in ("db", "both"):
                    session.add_all(new_flights)
                    await session.commit()
                    logger.debug(f"[Flight Summary] Saved {len(new_flights)} new records to DB.")

                if csv_rows and storage_mode in ("csv", "both") and csv_path:
                    write_csv(csv_rows, csv_path)
                    logger.debug(f"[Flight Summary] Appended {len(csv_rows)} records to CSV.")

                if max_takeoff == next_from or max_takeoff >= range_to:
                    break

                next_from = max_takeoff + timedelta(seconds=1)

        logger.debug("[Flight Summary] Query Fetch Date Ranges completed")

        if len(processing_flights) < 1:
            return None
        return processing_flights


@performance_timer
async def fetch_all_ranges(
        start_date: str,
        end_date: str,
        icao: Optional[str] = None,
        registrations: Optional[List[str]] = None,
        storage_mode: str = "both",
        csv_path: Optional[str] = FLIGHT_RADAR_PATH / f"flights_{datetime.strftime(datetime.now(), '%Y%m%d_%H%M')}.csv"
):
    if registrations is None and icao is None:
        client: DatabaseClient = DatabaseClient()
        async with client.session("main") as session:
            stmt = (
                select(
                    Registrations.reg
                )
                .where(Registrations.indashboard == True)
            )
            result = await session.execute(stmt)
            registrations = result.scalars().all()

    logger.info("[Flight Summary] Starting query Fetch All Ranges")

    start_dt = parse_date_or_datetime(start_date)
    end_dt = parse_date_or_datetime(end_date)

    date_ranges = []
    current = start_dt

    flights = []

    while current <= end_dt:
        range_end = min(current + timedelta(days=FLIGHT_RADAR_RANGE_DAYS) - timedelta(seconds=1), end_dt)
        date_ranges.append((current, range_end))
        current = range_end + timedelta(seconds=1)

    registration_batches = (
        [registrations[i:i + FLIGHT_RADAR_MAX_REG_PER_BATCH] for i in
         range(0, len(registrations), FLIGHT_RADAR_MAX_REG_PER_BATCH)]
        if registrations else [None]
    )

    async with aiohttp.ClientSession() as http:
        for batch_index, reg_batch in enumerate(registration_batches):
            if reg_batch:
                logger.debug(
                    f"\n[Flight Summary] Processing a batch of registrations {batch_index + 1} out of {len(registration_batches)}")
            for i, (range_start, range_end) in enumerate(date_ranges):
                logger.debug(f"[Flight Summary] Range {i + 1} out of {len(date_ranges)}")
                flights.append(await fetch_date_range(
                    icao=icao,
                    regs=reg_batch,
                    range_from=range_start,
                    range_to=range_end,
                    http=http,
                    storage_mode=storage_mode,
                    csv_path=csv_path
                ))
        logger.info("[Flight Summary] Query Fetch All Ranges completed")

        return flights



if __name__ == "__main__":
    # ICAO = "GLO, CEB, AVA"
    # ICAO = "UAE"
    # ICAO = "RSX"
    # ICAO = "VSV, ABY, RBG, CXI, RAM, VJC, CAI"
    # ICAO = "SAA, PGT"
    ICAO = None

    # START_DATE = "2022-06-02"
    START_DATE = "2026-01-22"
    END_DATE = "2026-02-01"

    storage_mode = "both"  # "db", "csv", or "both"

    REGISTRATIONS = None


    csv_path = FLIGHT_RADAR_PATH / f"flights_01_28_2026.csv"

    asyncio.run(fetch_all_ranges(
        start_date=START_DATE,
        end_date=END_DATE,
        icao=ICAO if ICAO else None,
        registrations=REGISTRATIONS if REGISTRATIONS else None,
        storage_mode=storage_mode
    ))
