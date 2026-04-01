from pathlib import Path
import random
from typing import Annotated

from fastapi import Request, status, Query, BackgroundTasks
from fastapi.responses import FileResponse

from API.FlightRadarAPI.FlightSummary import fetch_all_ranges
from Config import setup_logger, Router, RESPONSES_PATH
from Schemas import RequestFRFlightSummary, DefaultResponse
from Schemas.Enums import service
from Utils import success_response, warning_response, error_response

logger = setup_logger(name="flightradar_api")

FlightRadarResponses = {
    202: {"model": DefaultResponse, "description": "Success"},
    400: {"model": DefaultResponse, "description": "Bad Request"},
    500: {"model": DefaultResponse, "description": "Server error"},
}

router = Router(
    prefix="/flightradar",
    tags=[service.APITagsEnum.FLIGHTRADAR],
    responses=FlightRadarResponses,
)


@router.get("/flightsummary")
async def process_data(request: Request,
                       background_tasks: BackgroundTasks,
                       _payload: Annotated[RequestFRFlightSummary, Query()]):
    payload = RequestFRFlightSummary(
        **_payload.model_dump()
    )
    if not payload.regs and not payload.airlines:
        return warning_response(request=request, msg="At least one of 'regs' or 'airlines' must be provided")

    if not payload.start_date and not payload.end_date:
        return warning_response(request=request, msg="'start_date' and 'end_date' must be provided")

    try:
        start_date_str, end_date_str = payload.start_date.strftime("%Y-%m-%d"), payload.end_date.strftime("%Y-%m-%d")
        regs, airlines = payload.regs, payload.airlines
        if airlines:
            regs = None

        background_tasks.add_task(
            fetch_all_ranges,
            registrations=regs,
            icao=airlines,
            start_date=start_date_str,
            end_date=end_date_str,
            user=payload.user,
            correlation_id=request.state.correlation_id,
        )

        filename = f"{random.randint(10000, 99999)}.json"
        filepath = Path(RESPONSES_PATH / filename)
        filepath.write_text('{"ok": True}', encoding="utf-8")

        return FileResponse(
            filepath,
            media_type="application/json",
            filename=filename,
            background=background_tasks,
        )

        # return success_response(request=request, msg="Process started successfully", status_code=status.HTTP_202_ACCEPTED)
    except Exception as _ex:
        return error_response(request=request, exc=_ex)

