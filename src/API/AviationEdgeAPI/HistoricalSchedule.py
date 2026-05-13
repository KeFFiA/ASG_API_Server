import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List

import aiohttp
from sqlalchemy import select

from Config import setup_logger, AVIATION_EDGE_API_KEY, AVIATION_EDGE_URL, AVIATION_EDGE_SECONDS_BETWEEN_REQUESTS, \
    AVIATION_EDGE_MAX_BATCH_SIZE, AVIATION_EDGE_MAX_RANGE_DAYS, AVIATION_EDGE_PATH
from Database import DatabaseClient
from Database.Models import HistoricalSchedule
from Utils import (
    parse_date_or_datetime,
    parse_dt,
    ensure_naive_utc,
    write_csv,
    performance_timer
)

logger = setup_logger("aviationedge_historical")


def split_batches(data: Optional[List[str]], batch_size: int) -> List[Optional[List[str]]]:
    if not data:
        return [None]

    return [
        data[i:i + batch_size]
        for i in range(0, len(data), batch_size)
    ]


def chunk_date_ranges(
        start_date: datetime,
        end_date: datetime,
        max_days: int
) -> List[tuple[datetime, datetime]]:
    ranges = []

    current = start_date

    while current <= end_date:
        chunk_end = min(
            current + timedelta(days=max_days - 1),
            end_date
        )

        ranges.append((current, chunk_end))

        current = chunk_end + timedelta(days=1)

    return ranges


async def fetch_historical_schedule_chunk(
        airport_code: str,
        schedule_type: str,
        range_from: datetime,
        range_to: datetime,
        http: aiohttp.ClientSession,
        airline_iata: Optional[str] = None,
        flight_num: Optional[str] = None,
        storage_mode: str = "db",
        csv_path: Optional[Path] = None
) -> int:
    """
    storage_mode:
        - db
        - csv
        - both
    """

    client = DatabaseClient()

    logger.debug(
        f"[Historical Schedule] "
        f"{airport_code=} | "
        f"{schedule_type=} | "
        f"{range_from=} | "
        f"{range_to=} | "
        f"{airline_iata=}"
    )

    params = {
        "key": AVIATION_EDGE_API_KEY,
        "code": airport_code,
        "type": schedule_type,
        "date_from": range_from.strftime("%Y-%m-%d"),
        "date_to": range_to.strftime("%Y-%m-%d")
    }

    if airline_iata:
        params["airline_iata"] = airline_iata

    if flight_num:
        params["flight_num"] = flight_num

    await asyncio.sleep(AVIATION_EDGE_SECONDS_BETWEEN_REQUESTS)

    async with http.get(
            f"{AVIATION_EDGE_URL}/flightsHistory",
            params=params
    ) as resp:

        if resp.status != 200:
            logger.error(
                f"[Historical Schedule] "
                f"HTTP {resp.status}: {await resp.text()}"
            )
            return 0

        data = await resp.json()

        if not isinstance(data, list):
            logger.warning(
                f"[Historical Schedule] Unexpected response: {data}"
            )
            return 0

        if not data:
            logger.debug(
                f"[Historical Schedule] Empty response "
                f"for {airport_code}"
            )
            return 0

        rows_to_insert = []
        csv_rows = []

        async with client.session("aviationedge") as session:

            existing_ids = set()

            flight_keys = []

            for item in data:
                flight = item.get("flight", {})

                flight_iata = flight.get("iataNumber")
                flight_icao = flight.get("icaoNumber")

                dep = item.get("departure", {})
                arr = item.get("arrival", {})

                scheduled_time = parse_dt(
                    dep.get("scheduledTime")
                    or arr.get("scheduledTime")
                )

                flight_keys.append((
                    flight_iata,
                    flight_icao,
                    ensure_naive_utc(scheduled_time)
                ))

            if storage_mode in ("db", "both") and flight_keys:
                stmt = (
                    select(
                        HistoricalSchedule.type,
                        HistoricalSchedule.departure_scheduled_time,
                        HistoricalSchedule.departure_iata_code,
                        HistoricalSchedule.arrival_iata_code,
                        HistoricalSchedule.flight_number
                    )
                    .where(
                        HistoricalSchedule.departure_scheduled_time.between(
                            range_from,
                            range_to
                        )
                    )
                )

                existing = (await session.execute(stmt)).all()

                existing_ids = {
                    (
                        row[0],
                        row[1],
                        row[2],
                        row[3],
                        row[4]
                    )
                    for row in existing
                }

            for item in data:
                try:
                    departure = item.get("departure", {})
                    arrival = item.get("arrival", {})
                    airline = item.get("airline", {})
                    flight = item.get("flight", {})
                    codeshared = item.get("codeshared", {})

                    codeshared_airline = codeshared.get("airline", {})
                    codeshared_flight = codeshared.get("flight", {})

                    departure_scheduled = ensure_naive_utc(
                        parse_dt(departure.get("scheduledTime"))
                    )

                    unique_key = (
                        item.get("type"),
                        departure_scheduled,
                        departure.get("iataCode"),
                        arrival.get("iataCode"),
                        flight.get("number")
                    )

                    if unique_key in existing_ids:
                        logger.debug(
                            f"[Historical Schedule] Duplicate skipped: "
                            f"{unique_key}"
                        )
                        continue

                    row_data = {
                        "type": item.get("type"),
                        "status": item.get("status"),

                        # Departure
                        "departure_iata_code": departure.get("iataCode"),
                        "departure_icao_code": departure.get("icaoCode"),
                        "departure_terminal": departure.get("terminal"),
                        "departure_gate": departure.get("gate"),
                        "departure_delay": departure.get("delay"),

                        "departure_scheduled_time": departure_scheduled,
                        "departure_estimated_time": ensure_naive_utc(
                            parse_dt(departure.get("estimatedTime"))
                        ),
                        "departure_actual_time": ensure_naive_utc(
                            parse_dt(departure.get("actualTime"))
                        ),
                        "departure_estimated_runway": ensure_naive_utc(
                            parse_dt(departure.get("estimatedRunway"))
                        ),
                        "departure_actual_runway": ensure_naive_utc(
                            parse_dt(departure.get("actualRunway"))
                        ),

                        # Arrival
                        "arrival_iata_code": arrival.get("iataCode"),
                        "arrival_icao_code": arrival.get("icaoCode"),
                        "arrival_terminal": arrival.get("terminal"),
                        "arrival_baggage": arrival.get("baggage"),
                        "arrival_gate": arrival.get("gate"),
                        "arrival_delay": arrival.get("delay"),

                        "arrival_scheduled_time": ensure_naive_utc(
                            parse_dt(arrival.get("scheduledTime"))
                        ),
                        "arrival_estimated_time": ensure_naive_utc(
                            parse_dt(arrival.get("estimatedTime"))
                        ),
                        "arrival_actual_time": ensure_naive_utc(
                            parse_dt(arrival.get("actualTime"))
                        ),
                        "arrival_estimated_runway": ensure_naive_utc(
                            parse_dt(arrival.get("estimatedRunway"))
                        ),
                        "arrival_actual_runway": ensure_naive_utc(
                            parse_dt(arrival.get("actualRunway"))
                        ),

                        # Airline
                        "airline_name": airline.get("name"),
                        "airline_iata_code": airline.get("iataCode"),
                        "airline_icao_code": airline.get("icaoCode"),

                        # Flight
                        "flight_number": flight.get("number"),
                        "flight_iata_number": flight.get("iataNumber"),
                        "flight_icao_number": flight.get("icaoNumber"),

                        # Codeshared Airline
                        "codeshared_airline_name": codeshared_airline.get("name"),
                        "codeshared_airline_iata_code": codeshared_airline.get("iataCode"),
                        "codeshared_airline_icao_code": codeshared_airline.get("icaoCode"),

                        # Codeshared Flight
                        "codeshared_flight_number": codeshared_flight.get("number"),
                        "codeshared_flight_iata_number": codeshared_flight.get("iataNumber"),
                        "codeshared_flight_icao_number": codeshared_flight.get("icaoNumber")
                    }

                    if storage_mode in ("db", "both"):
                        rows_to_insert.append(
                            HistoricalSchedule(**row_data)
                        )

                    if storage_mode in ("csv", "both"):
                        csv_rows.append(row_data)

                except Exception as e:
                    logger.warning(
                        f"[Historical Schedule] Parse error: {e}"
                    )

            if rows_to_insert and storage_mode in ("db", "both"):
                session.add_all(rows_to_insert)
                await session.commit()

                logger.debug(
                    f"[Historical Schedule] "
                    f"Inserted {len(rows_to_insert)} rows"
                )

            if csv_rows and storage_mode in ("csv", "both") and csv_path:
                write_csv(csv_rows, csv_path.as_posix())

                logger.debug(
                    f"[Historical Schedule] "
                    f"Written {len(csv_rows)} rows to CSV"
                )

            return len(rows_to_insert) + len(csv_rows)


@performance_timer
async def fetch_historical_schedules(
        airport_codes: List[str],
        schedule_types: List[str],
        start_date: str,
        end_date: str,
        airline_iata_codes: Optional[List[str]] = None,
        storage_mode: str = "db",
        csv_path: Optional[Path] = AVIATION_EDGE_PATH / (
                f"historical_schedules_"
                f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
):
    """
    storage_mode:
        - db
        - csv
        - both
    """

    logger.info("[Historical Schedule] Starting fetch")

    start_dt = parse_date_or_datetime(start_date)
    end_dt = parse_date_or_datetime(end_date)

    date_ranges = chunk_date_ranges(
        start_dt,
        end_dt,
        AVIATION_EDGE_MAX_RANGE_DAYS
    )

    airline_batches = split_batches(
        airline_iata_codes,
        AVIATION_EDGE_MAX_BATCH_SIZE
    )

    total_saved = 0

    async with aiohttp.ClientSession() as http:

        for range_start, range_end in date_ranges:

            for airport_code in airport_codes:

                for schedule_type in schedule_types:

                    for airline_batch in airline_batches:

                        if not airline_batch:
                            airline_batch = [None]

                        for airline_iata in airline_batch:
                            logger.info(
                                f"[Historical Schedule] "
                                f"{airport_code=} | "
                                f"{schedule_type=} | "
                                f"{airline_iata=} | "
                                f"{range_start.date()} -> {range_end.date()}"
                            )

                            saved = await fetch_historical_schedule_chunk(
                                airport_code=airport_code,
                                schedule_type=schedule_type,
                                range_from=range_start,
                                range_to=range_end,
                                airline_iata=airline_iata,
                                http=http,
                                storage_mode=storage_mode,
                                csv_path=csv_path
                            )

                            total_saved += saved

    logger.info(
        f"[Historical Schedule] Completed. "
        f"Total saved: {total_saved}"
    )

    return total_saved


if __name__ == "__main__":
    import asyncio
    from Utils import str_to_list

    AIRPORTS = str_to_list(
        """
        DXB
        """.upper()
    )

    AIRLINES = str_to_list(
        """
        EK
        """.upper()
    )

    SCHEDULE_TYPES = ["departure"]

    START_DATE = "2025-06-01"
    END_DATE = "2025-06-30"

    SAVE_MODE = "both"
    CSV_NAME = "test"

    asyncio.run(
        fetch_historical_schedules(
            airport_codes=AIRPORTS,
            airline_iata_codes=AIRLINES if AIRLINES else None,
            schedule_types=SCHEDULE_TYPES,
            start_date=START_DATE,
            end_date=END_DATE,
            storage_mode=SAVE_MODE,
            csv_path=(AVIATION_EDGE_PATH / CSV_NAME) if CSV_NAME else None,
        )
    )


