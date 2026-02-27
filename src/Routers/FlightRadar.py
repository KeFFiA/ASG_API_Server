from typing import Annotated

from fastapi import APIRouter, Request, status, Query, BackgroundTasks
from fastapi.responses import JSONResponse

from API.FlightRadarAPI.FlightSummary import fetch_all_ranges
from Config import setup_logger
from Schemas import ErrorValidationResponse, ErrorResponse, SuccessDataResponse, DetailField, RequestFRFlightSummary
from Schemas.Enums import service

logger = setup_logger(name="flightradar_api")

router = APIRouter(
    prefix="/flightradar",
    tags=[service.APITagsEnum.FLIGHTRADAR],
    responses={422: {"model": ErrorValidationResponse}},
)


FlightRadarResponses = {
    200: {"model": SuccessDataResponse, "description": "Success"},
    400: {"model": ErrorResponse, "description": "Bad Request"},
    500: {"model": ErrorResponse, "description": "Server error"},
}


@router.post("/flightsummary")
async def process_data(request: Request,
                       background_tasks: BackgroundTasks,
                       _payload: Annotated[RequestFRFlightSummary, Query()]):
    payload = RequestFRFlightSummary(
        **_payload.model_dump()
    )
    if not payload.regs and not payload.airlines:
        response = ErrorResponse(
            correlationId=request.state.correlation_id,
            code=status.HTTP_400_BAD_REQUEST,
            detail=[DetailField(msg="At least one of 'regs' or 'airlines' must be provided.")]
        )
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=response.model_dump(mode="json"))

    if not payload.start_date and not payload.end_date:
        response = ErrorResponse(
            correlationId=request.state.correlation_id,
            code=status.HTTP_400_BAD_REQUEST,
            detail=[DetailField(msg="'start_date' and 'end_date' must be provided.")]
        )
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=response.model_dump(mode="json"))

    start_date_str, end_date_str = payload.start_date.strftime("%Y-%m-%d"), payload.end_date.strftime("%Y-%m-%d")
    regs, airlines = payload.regs, payload.airlines

    background_tasks.add_task(
        fetch_all_ranges,
        registrations=regs,
        icao=airlines,
        start_date=start_date_str,
        end_date=end_date_str,
        user=payload.user,
        correlation_id=request.state.correlation_id,
    )

    response = SuccessDataResponse(
        correlationId=request.state.correlation_id,
        code=status.HTTP_200_OK,
        detail=[DetailField(msg="Process started successfully.")],
        data=[{"ok": True}]
    )
    return JSONResponse(status_code=status.HTTP_200_OK, content=response.model_dump(mode="json"))
