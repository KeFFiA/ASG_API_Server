from typing import Annotated

from fastapi import status, Request, Query, Body

from Config import setup_logger, Router
from Schemas import DefaultResponse, AirlinesQuery, AircraftTemplatesQuery, AircraftsQuery, CreateAircraftQuery, \
    CreateAirlinesBody, CreateAircraftTemplatesBody, AircraftsAdditionalQuery
from Schemas.Enums import service
from Utils import DBProxy, success_response, error_response, warning_response
from .DBQueries.AircraftsAirlines import query_airline, query_create_airline, query_templates, query_create_template, \
    query_create_aircraft, query_aircrafts, query_aircraft_additional

logger = setup_logger(name="msgraph_aircrafts_airlines")

MSGraphResponses = {
    200: {"model": DefaultResponse, "description": "Success"},
    201: {"model": DefaultResponse, "description": "Created"},
    400: {"model": DefaultResponse, "description": "Bad Request"},
    404: {"model": DefaultResponse, "description": "Not found"},
    500: {"model": DefaultResponse, "description": "Server error"},
}

router = Router(
    prefix="/msgraph/aircrafts_airlines",
    tags=[service.APITagsEnum.MSGRAPH],
    responses=MSGraphResponses,
)


@router.get(
    path="/airlines",
    description="Get Airlines",
    status_code=status.HTTP_200_OK,
    response_model=DefaultResponse,
)
async def get_airlines(request: Request, _payload: Annotated[AirlinesQuery, Query()]):
    payload = AirlinesQuery(
        **_payload.model_dump()
    )

    if sum(p is not None
           for p in (payload.airline_name, payload.airline_id, payload.user_id)
           ) == 3:
        return warning_response(
            request=request,
            msg="Exactly one of 'airline_name', 'airline_id' or 'user_id' must be provided"
        )

    db_proxy: DBProxy = request.state.db_proxy

    async def db_query(session):
        return await query_airline(session, airline_name=payload.airline_name, airline_id=payload.airline_id,
                                   user_id=payload.user_id)

    try:
        if payload.user_id:
            cache_key = f"airline:{payload.user_id}"
        elif payload.airline_name:
            cache_key = f"airline:{payload.airline_name}"
        elif payload.airline_id:
            cache_key = f"airline:{payload.airline_id}"
        else:
            cache_key = "airline:all"
        airline_data = await db_proxy.get_or_cache(
            key=cache_key,
            db_name="powerplatform",
            query_func=db_query,
            ttl=60
        )
        if len(airline_data) > 0:
            return success_response(request=request, data=airline_data, msg="Airline(-s) retrieved successfully")
        return warning_response(request=request, msg="Airline(-s) not found", status_code=status.HTTP_404_NOT_FOUND)

    except ValueError:
        return warning_response(request=request, msg="Airline(-s) not found", status_code=status.HTTP_404_NOT_FOUND)
    except Exception as _ex:
        logger.error(f"Failed to get Airline(-s): {_ex}")
        return error_response(request=request, exc=_ex)


@router.post(
    path="/airlines",
    description="Create Airlines",
    status_code=status.HTTP_201_CREATED,
    response_model=DefaultResponse,
)
async def create_airlines(request: Request, _payload: Annotated[CreateAirlinesBody, Body()]):
    payload = CreateAirlinesBody(
        **_payload.model_dump()
    )

    if not payload.airline_name and not payload.airline_icao:
        return warning_response(
            request=request,
            msg="Both 'airline_name' and 'airline_icao' must be provided"
        )

    db_proxy: DBProxy = request.state.db_proxy

    async def db_query(session):
        return await query_create_airline(session, airline_name=payload.airline_name, airline_icao=payload.airline_icao,
                                          user_id=payload.user_id, file_data=payload.file_data)

    try:
        cache_key = f"airline:{payload.airline_icao}"
        await db_proxy.update_and_cache(
            key=cache_key,
            db_name="powerplatform",
            update_func=db_query,
            ttl=60
        )

        return success_response(request=request, msg="Airline created successfully",
                                status_code=status.HTTP_201_CREATED)

    except Exception as _ex:
        logger.error(f"Failed to create airline: {_ex}")
        return error_response(request=request, exc=_ex)


@router.get(
    path="/aircrafts/templates",
    description="Get Aircraft templates",
    status_code=status.HTTP_200_OK,
    response_model=DefaultResponse,
)
async def get_aircraft_template(request: Request, _payload: Annotated[AircraftTemplatesQuery, Query()]):
    payload = AircraftTemplatesQuery(
        **_payload.model_dump()
    )

    if sum(p is not None
           for p in (payload.template_id, payload.template_name)
           ) == 2:
        return warning_response(
            request=request,
            msg="Exactly one of 'template_id' or 'template_name' must be provided"
        )

    db_proxy: DBProxy = request.state.db_proxy

    async def db_query(session):
        return await query_templates(session, template_name=payload.template_name, template_id=payload.template_id)

    try:
        if payload.template_id:
            cache_key = f"aircraft_template:{payload.template_id}"
        elif payload.template_name:
            cache_key = f"aircraft_template:{payload.template_name}"
        else:
            cache_key = "aircraft_template:all"
        aircraft_template_data = await db_proxy.get_or_cache(
            key=cache_key,
            db_name="powerplatform",
            query_func=db_query,
            ttl=60
        )
        if len(aircraft_template_data) > 0:
            return success_response(request=request, data=aircraft_template_data,
                                    msg="Aircraft template(-s) retrieved successfully")
        return warning_response(request=request, msg="Aircraft template(-s) not found",
                                status_code=status.HTTP_404_NOT_FOUND)

    except ValueError:
        return warning_response(request=request, msg="Aircraft template(-s) not found",
                                status_code=status.HTTP_404_NOT_FOUND)
    except Exception as _ex:
        logger.error(f"Failed to get Aircraft template(-s): {_ex}")
        return error_response(request=request, exc=_ex)


@router.post(
    path="/aircrafts/templates",
    description="Create Aircraft template",
    status_code=status.HTTP_201_CREATED,
    response_model=DefaultResponse,
)
async def create_aircraft_template(request: Request, _payload: Annotated[CreateAircraftTemplatesBody, Body()]):
    payload = CreateAircraftTemplatesBody(
        **_payload.model_dump()
    )

    if not payload.template_name:
        return warning_response(request=request, msg="'template_name' must be provided")

    db_proxy: DBProxy = request.state.db_proxy

    async def db_query(session):
        return await query_create_template(session, template_name=payload.template_name, file_data=payload.file_data)

    try:
        cache_key = f"template:{payload.template_name}"
        await db_proxy.update_and_cache(
            key=cache_key,
            db_name="powerplatform",
            update_func=db_query,
            ttl=60
        )

        return success_response(request=request, msg="Aircraft template created successfully",
                                status_code=status.HTTP_201_CREATED)

    except Exception as _ex:
        logger.error(f"Failed to create Aircraft template: {_ex}")
        return error_response(request=request, exc=_ex)


@router.get(
    path="/aircrafts",
    description="Get Aircrafts",
    status_code=status.HTTP_200_OK,
    response_model=DefaultResponse,
)
async def get_aircrafts(request: Request, _payload: Annotated[AircraftsQuery, Query()]):
    payload = AircraftsQuery(
        **_payload.model_dump()
    )

    if sum(p is not None
           for p in (payload.template_id, payload.template_name, payload.aircraft_registration, payload.aircraft_id,
                     payload.airline_id, payload.airline_name, payload.aircraft_msn)
           ) == 7:
        return warning_response(
            request=request,
            msg=(
                "Exactly one of 'template_id', 'template_name', 'aircraft_registration', 'aircraft_msn', 'aircraft_id', \n"
                "'airline_id' or 'airline_name' must be provided")
        )

    db_proxy: DBProxy = request.state.db_proxy

    async def db_query(session):
        return await query_aircrafts(session, airline_id=payload.airline_id, template_id=payload.template_id,
                                     template_name=payload.template_name,
                                     aircraft_registration=payload.aircraft_registration,
                                     aircraft_id=payload.aircraft_id, aircraft_msn=payload.aircraft_msn,
                                     airline_name=payload.airline_name)

    try:
        if payload.template_id:
            cache_key = f"aircraft:{payload.template_id}"
        elif payload.template_name:
            cache_key = f"aircraft:{payload.template_name}"
        elif payload.aircraft_registration:
            cache_key = f"aircraft:{payload.aircraft_registration}"
        elif payload.aircraft_id:
            cache_key = f"aircraft:{payload.aircraft_id}"
        elif payload.airline_id:
            cache_key = f"aircraft:{payload.airline_id}"
        elif payload.airline_name:
            cache_key = f"aircraft:{payload.airline_name}"
        elif payload.aircraft_msn:
            cache_key = f"aircraft:{payload.aircraft_msn}"
        else:
            cache_key = "aircrafts:all"
        aircraft_data = await db_proxy.get_or_cache(
            key=cache_key,
            db_name="powerplatform",
            query_func=db_query,
            ttl=60
        )
        if len(aircraft_data) > 0:
            return success_response(request=request, data=aircraft_data,
                                    msg="Aircraft retrieved successfully")
        return warning_response(request=request, msg="Aircraft not found",
                                status_code=status.HTTP_404_NOT_FOUND)

    except ValueError:
        return warning_response(request=request, msg="Aircraft not found",
                                status_code=status.HTTP_404_NOT_FOUND)
    except Exception as _ex:
        logger.error(f"Failed to get Aircraft: {_ex}")
        return error_response(request=request, exc=_ex)


@router.post(
    path="/aircrafts",
    description="Create Aircraft",
    status_code=status.HTTP_201_CREATED,
    response_model=DefaultResponse,
)
async def create_aircraft(request: Request, _payload: Annotated[CreateAircraftQuery, Query()]):
    payload = CreateAircraftQuery(
        **_payload.model_dump()
    )

    if not payload.airline_id and not payload.template_id and not payload.aircraft_msn and not payload.aircraft_registration:
        return warning_response(request=request,
                                msg="'airline_id', 'template_id', 'aircraft_msn' and 'aircraft_registration' must be provided")

    db_proxy: DBProxy = request.state.db_proxy

    async def db_query(session):
        return await query_create_aircraft(session, **payload.model_dump())

    try:
        cache_key = f"aircraft:{payload.aircraft_registration}"
        await db_proxy.update_and_cache(
            key=cache_key,
            db_name="powerplatform",
            update_func=db_query,
            ttl=60
        )

        return success_response(request=request, msg="Aircraft created successfully",
                                status_code=status.HTTP_201_CREATED)

    except Exception as _ex:
        logger.error(f"Failed to create Aircraft: {_ex}")
        return error_response(request=request, exc=_ex)


@router.get(
    path="/aircrafts/additional",
    description="Get Aircrafts additional information",
    status_code=status.HTTP_200_OK,
    response_model=DefaultResponse,
)
async def get_aircrafts_additional(request: Request, _payload: Annotated[AircraftsAdditionalQuery, Query()]):
    payload = AircraftsAdditionalQuery(
        **_payload.model_dump()
    )

    db_proxy: DBProxy = request.state.db_proxy

    async def db_query(session):
        return await query_aircraft_additional(session, aircraft_id=payload.aircraft_id)

    try:
        cache_key = f"aircrafts_additional:{payload.aircraft_id}"
        aircraft_data = await db_proxy.get_or_cache(
            key=cache_key,
            db_name="aixii_cirium",
            query_func=db_query,
            ttl=60
        )
        if len(aircraft_data) > 0:
            return success_response(request=request, data=aircraft_data,
                                    msg="Aircraft additional info retrieved successfully")
        return warning_response(request=request, msg="Aircraft not found",
                                status_code=status.HTTP_404_NOT_FOUND)

    except ValueError:
        return warning_response(request=request, msg="Aircraft not found",
                                status_code=status.HTTP_404_NOT_FOUND)
    except Exception as _ex:
        logger.error(f"Failed to get Aircraft additional info: {_ex}")
        return error_response(request=request, exc=_ex)
