from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List

import asyncio
import aiohttp
import orjson
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from Config import setup_logger, AVIATION_EDGE_API_KEY, AVIATION_EDGE_URL, AVIATION_EDGE_MAX_BATCH_SIZE, \
    AVIATION_EDGE_MAX_RANGE_DAYS, AVIATION_EDGE_PATH, AVIATION_EDGE_EXTRA_API_KEY
from Database import DatabaseClient
from Database.Models import HistoricalSchedule
from Utils import parse_date_or_datetime, parse_dt, write_csv, performance_timer, ensure_utc


logger = setup_logger("aviationedge_historical")


MAX_CONCURRENT_REQUESTS = 5
BULK_INSERT_SIZE = 5000 # TODO: Move to config
DB_INSERT_BATCH_SIZE = 650


def chunked(iterable, size):
    for i in range(0, len(iterable), size):
        yield iterable[i:i + size]


def split_batches(
        data: Optional[List[str]],
        batch_size: int
) -> List[List[str]]:
    if not data:
        return [[]]

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


async def bulk_insert_historical_schedule(
        session: AsyncSession,
        rows: List[dict]
) -> int:

    total_inserted = 0

    for batch in chunked(rows, DB_INSERT_BATCH_SIZE):

        stmt = insert(HistoricalSchedule).values(batch)

        stmt = stmt.on_conflict_do_nothing(
            index_elements=[
                "type",
                "departure_scheduled_time",
                "departure_iata_code",
                "arrival_iata_code",
                "flight_number"
            ]
        )

        result = await session.execute(stmt)

        total_inserted += result.rowcount or 0

    return total_inserted


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

    params = {
        "key": AVIATION_EDGE_API_KEY,
        "code": airport_code,
        "type": schedule_type,
        "date_from": range_from.strftime("%Y-%m-%d"),
        "date_to": range_to.strftime("%Y-%m-%d"),
        "extra_key": AVIATION_EDGE_EXTRA_API_KEY
    }

    if airline_iata:
        params["airline_iata"] = airline_iata

    if flight_num:
        params["flight_num"] = flight_num

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

        try:
            raw = await resp.read()
            data = orjson.loads(raw)

        except Exception as e:
            logger.error(
                f"[Historical Schedule] JSON parse error: {e}"
            )
            return 0

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

        parse_errors = 0

        for item in data:

            try:
                departure = item.get("departure", {})
                arrival = item.get("arrival", {})
                airline = item.get("airline", {})
                flight = item.get("flight", {})
                codeshared = item.get("codeshared", {})

                codeshared_airline = codeshared.get("airline", {})
                codeshared_flight = codeshared.get("flight", {})

                departure_scheduled = ensure_utc(
                    parse_dt(departure.get("scheduledTime"))
                )

                row_data = {
                    # Base
                    "type": item.get("type"),
                    "status": item.get("status"),

                    # Departure
                    "departure_iata_code": departure.get("iataCode"),
                    "departure_icao_code": departure.get("icaoCode"),
                    "departure_terminal": departure.get("terminal"),
                    "departure_gate": departure.get("gate"),
                    "departure_delay": departure.get("delay"),

                    "departure_scheduled_time": departure_scheduled,
                    "departure_estimated_time": ensure_utc(
                        parse_dt(departure.get("estimatedTime"))
                    ),
                    "departure_actual_time": ensure_utc(
                        parse_dt(departure.get("actualTime"))
                    ),
                    "departure_estimated_runway": ensure_utc(
                        parse_dt(departure.get("estimatedRunway"))
                    ),
                    "departure_actual_runway": ensure_utc(
                        parse_dt(departure.get("actualRunway"))
                    ),

                    # Arrival
                    "arrival_iata_code": arrival.get("iataCode"),
                    "arrival_icao_code": arrival.get("icaoCode"),
                    "arrival_terminal": arrival.get("terminal"),
                    "arrival_baggage": arrival.get("baggage"),
                    "arrival_gate": arrival.get("gate"),
                    "arrival_delay": arrival.get("delay"),

                    "arrival_scheduled_time": ensure_utc(
                        parse_dt(arrival.get("scheduledTime"))
                    ),
                    "arrival_estimated_time": ensure_utc(
                        parse_dt(arrival.get("estimatedTime"))
                    ),
                    "arrival_actual_time": ensure_utc(
                        parse_dt(arrival.get("actualTime"))
                    ),
                    "arrival_estimated_runway": ensure_utc(
                        parse_dt(arrival.get("estimatedRunway"))
                    ),
                    "arrival_actual_runway": ensure_utc(
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

                    # Codeshare Airline
                    "codeshared_airline_name": codeshared_airline.get("name"),
                    "codeshared_airline_iata_code": codeshared_airline.get("iataCode"),
                    "codeshared_airline_icao_code": codeshared_airline.get("icaoCode"),

                    # Codeshare Flight
                    "codeshared_flight_number": codeshared_flight.get("number"),
                    "codeshared_flight_iata_number": codeshared_flight.get("iataNumber"),
                    "codeshared_flight_icao_number": codeshared_flight.get("icaoNumber")
                }

                if storage_mode in ("db", "both"):
                    rows_to_insert.append(row_data)

                if storage_mode in ("csv", "both"):
                    csv_rows.append(row_data)

            except Exception as e:
                parse_errors += 1

                logger.warning(
                    f"[Historical Schedule] Parse error: {e}"
                )

        inserted = 0


        if rows_to_insert and storage_mode in ("db", "both"):

            try:
                client = DatabaseClient()

                async with client.session("aviationedge") as session:

                    inserted = await bulk_insert_historical_schedule(
                        session=session,
                        rows=rows_to_insert
                    )

                    await session.commit()

                logger.info(
                    f"[Historical Schedule] "
                    f"Inserted {inserted}/{len(rows_to_insert)} "
                    f"rows | "
                    f"{airport_code=} | "
                    f"{schedule_type=} | "
                    f"{range_from.date()} -> {range_to.date()}"
                )

            except Exception as e:
                logger.exception(
                    f"[Historical Schedule] Bulk insert failed: {e}"
                )

        if csv_rows and storage_mode in ("csv", "both") and csv_path:

            try:
                write_csv(csv_rows, csv_path.as_posix())

                logger.info(
                    f"[Historical Schedule] "
                    f"Written {len(csv_rows)} rows to CSV"
                )

            except Exception as e:
                logger.exception(
                    f"[Historical Schedule] CSV write failed: {e}"
                )

        if parse_errors:
            logger.warning(
                f"[Historical Schedule] "
                f"Parse errors: {parse_errors}"
            )

        return inserted


async def fetch_with_semaphore(
        sem: asyncio.Semaphore,
        **kwargs
):
    async with sem:
        return await fetch_historical_schedule_chunk(**kwargs)


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
        ),
        resume_from: int = 0
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

    airline_batch_sizes = [
        len(batch) if batch else 1
        for batch in airline_batches
    ]

    total_iterations = (
            len(date_ranges)
            * len(airport_codes)
            * len(schedule_types)
            * sum(airline_batch_sizes)
    )

    current_iteration = 0
    total_saved = 0

    sem = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    connector = aiohttp.TCPConnector(
        limit=MAX_CONCURRENT_REQUESTS,
        ttl_dns_cache=300
    )

    timeout = aiohttp.ClientTimeout(
        total=120
    )

    client = DatabaseClient()

    async with (
        aiohttp.ClientSession(
            connector=connector,
            timeout=timeout
        ) as http,

        client.session("aviationedge") as session
    ):

        tasks = []

        for range_start, range_end in date_ranges:

            for airport_code in airport_codes:

                for schedule_type in schedule_types:

                    for airline_batch in airline_batches:

                        if not airline_batch:
                            airline_batch = [None]

                        for airline_iata in airline_batch:

                            current_iteration += 1

                            if current_iteration < resume_from:
                                continue

                            logger.info(
                                f"[Historical Schedule] "
                                f"Progress "
                                f"{current_iteration}/{total_iterations} | "
                                f"{airport_code=} | "
                                f"{schedule_type=} | "
                                f"{airline_iata=} | "
                                f"{range_start.date()} -> "
                                f"{range_end.date()}"
                            )

                            tasks.append(
                                fetch_with_semaphore(
                                    sem=sem,
                                    airport_code=airport_code,
                                    schedule_type=schedule_type,
                                    range_from=range_start,
                                    range_to=range_end,
                                    airline_iata=airline_iata,
                                    http=http,
                                    storage_mode=storage_mode,
                                    csv_path=csv_path
                                )
                            )

        logger.info(
            f"[Historical Schedule] "
            f"Executing {len(tasks)} tasks"
        )

        results = await asyncio.gather(
            *tasks,
            return_exceptions=True
        )

        for result in results:

            if isinstance(result, Exception):
                logger.exception(
                    f"[Historical Schedule] Task failed: {result}"
                )
                continue

            total_saved += result

        await session.commit()

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
AAN
ABJ
ACC
ADD
ADL
AGP
AKL
ALA
ALG
AMD
AMM
AMS
ANC
ARN
ATH
AUH
AVV
BAH
BCN
BEY
BGW
BHX
BKK
BLQ
BLR
BNE
BOG
BOM
BOS
BQN
BRU
BSR
BUD
CAI
CAN
CCU
CDG
CEB
CGK
CGO
CHC
CKY
CLO
CMB
CMN
COK
COO
CPH
CPT
CRK
CTU
CVG
DAC
DAD
DAM
DAR
DEL
DFW
DME
DMK
DMM
DOH
DPS
DSS
DTW
DUB
DUR
DUS
DWC
DXB
EBB
EBL
EDI
EMA
EWR
EZE
FCO
FLL
FRA
GIG
GLA
GRU
GVA
GYD
HAJ
HAM
HAN
HGH
HKG
HKT
HND
HRE
HTT
HYD
IAD
IAH
ICN
IKA
ISB
ISL
IST
JED
JFK
JNB
KEF
KHH
KHI
KHN
KIX
KTI
KUL
KWI
LAD
LAX
LBG
LCA
LED
LGG
LGW
LHE
LHR
LIS
LLW
LOS
LPL
LUN
LYS
MAA
MAD
MAN
MBA
MCO
MCT
MEB
MED
MEL
MEX
MIA
MLA
MLE
MNL
MRU
MST
MUC
MXP
NBJ
NBO
NCE
NCL
NHD
NKC
NLU
NQY
NRT
OAK
OHS
OKC
ORD
OSF
OSL
PAE
PEK
PER
PEW
PKX
PNH
PRG
PVG
QEC
QUA
RFD
RKT
RMB
RUH
SAI
SEA
SEZ
SFO
SGN
SHJ
SIN
SKT
STN
SYD
SYZ
SZX
TAN
TEV
THR
TLS
TNR
TPE
TRV
TUN
UIO
UTP
VCE
VIE
WAW
XMN
YUL
YYZ
ZAZ
ZDY
ZIA
ZRH
        """.upper()
    )

    AIRLINES = str_to_list(
        """
        EK
        """.upper()
    )

    SCHEDULE_TYPES = ["departure"]

    START_DATE = "2024-01-01"
    END_DATE = "2025-06-30"

    SAVE_MODE = "both"
    CSV_NAME = "data_22_05_26(2024-01-01 - 2025-06-30).csv"

    asyncio.run(
        fetch_historical_schedules(
            airport_codes=AIRPORTS,
            airline_iata_codes=AIRLINES if AIRLINES else None,
            schedule_types=SCHEDULE_TYPES,
            start_date=START_DATE,
            end_date=END_DATE,
            storage_mode=SAVE_MODE,
            csv_path=(AVIATION_EDGE_PATH / CSV_NAME) if CSV_NAME else None,
            resume_from=0
        )
    )
