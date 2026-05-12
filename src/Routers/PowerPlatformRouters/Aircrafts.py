from typing import Annotated, List

from fastapi import status, Request, Query, Body, Response

from Config import setup_logger, Router
from Schemas import DefaultResponse, TemplateSchemaLight, TemplateSchemaFull, AircraftSchemaFull, AircraftSchemaLight, \
    EngineSchema, AdditionalAircraftInfoSchema, EngineTypeSchema
from Schemas.Enums import service
from Schemas.PowerPlatform.BodySchemas.AircraftSchemas import CreateAircraftTemplatesBody, CreateUpdateAircraftBody
from Schemas.PowerPlatform.QuerySchemas.AircraftSchemas import GetAircraftQuery, GetEngineTypeQuery, \
    GetAircraftTemplateQuery, GetAircraftIDQuery
from Utils import DBProxy, success_response, error_response, warning_response, cache_key_first_non_null
from .DBQueries.Aircrafts import query_aircrafts, query_get_engines_type, query_templates, query_create_template, \
    query_create_update_aircraft, query_aircraft_additional, query_get_engines
from Utils.ResponsesFunc import build_responses

logger = setup_logger(name="powerplatform_aircrafts")

router = Router(
    prefix="/powerplatform/aircrafts",
    tags=[service.APITagsEnum.AIRCRAFTS],
)


@router.get(
    path="/templates/full",
    description="Get Aircraft templates",
    status_code=status.HTTP_200_OK,
    response_model=DefaultResponse[List[TemplateSchemaFull]],
    responses=build_responses(
        include={status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_500_INTERNAL_SERVER_ERROR}
    )
)
async def get_aircraft_template_full(request: Request, response: Response, _payload: Annotated[GetAircraftTemplateQuery, Query()]):
    db_proxy: DBProxy = request.state.db_proxy

    async def db_query(session):
        return await query_templates(session, _payload=_payload, full=True)

    try:
        cache_key = cache_key_first_non_null(name="aircraft_template:full", data=_payload.model_dump(),
                                 keys=("template_id", "template_name"),
                                 fallback="all")
        aircraft_template_data = await db_proxy.get_or_cache(
            key=cache_key,
            db_name="powerplatform",
            query_func=db_query,
            ttl=60
        )
        if len(aircraft_template_data) > 0:
            return success_response(request=request, response=response, data=aircraft_template_data,
                                    msg="Aircraft template(-s) retrieved successfully")
        return warning_response(request=request, response=response, msg="Aircraft template(-s) not found",
                                status_code=status.HTTP_404_NOT_FOUND)

    except ValueError:
        return warning_response(request=request, response=response, msg="Aircraft template(-s) not found",
                                status_code=status.HTTP_404_NOT_FOUND)
    except Exception as _ex:
        logger.error(f"Failed to get Aircraft template(-s): {_ex}")
        return error_response(request=request, response=response, exc=_ex)


@router.get(
    path="/templates/light",
    description="Get Aircraft templates",
    status_code=status.HTTP_200_OK,
    response_model=DefaultResponse[List[TemplateSchemaLight]],
    responses=build_responses(
            include={status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_500_INTERNAL_SERVER_ERROR}
        )
)
async def get_aircraft_template_light(request: Request, response: Response, _payload: Annotated[GetAircraftTemplateQuery, Query()]):
    db_proxy: DBProxy = request.state.db_proxy

    async def db_query(session):
        return await query_templates(session, _payload=_payload, full=False)

    try:
        cache_key = cache_key_first_non_null(name="aircraft_template:light", data=_payload.model_dump(),
                                 keys=(
                                     "template_id", "template_name"),
                                 fallback="all")
        aircraft_template_data = await db_proxy.get_or_cache(
            key=cache_key,
            db_name="powerplatform",
            query_func=db_query,
            ttl=60
        )
        if len(aircraft_template_data) > 0:
            return success_response(request=request, response=response, data=aircraft_template_data,
                                    msg="Aircraft template(-s) retrieved successfully")
        return warning_response(request=request, response=response, msg="Aircraft template(-s) not found",
                                status_code=status.HTTP_404_NOT_FOUND)

    except ValueError:
        return warning_response(request=request, response=response, msg="Aircraft template(-s) not found",
                                status_code=status.HTTP_404_NOT_FOUND)
    except Exception as _ex:
        logger.error(f"Failed to get Aircraft template(-s): {_ex}")
        return error_response(request=request, response=response, exc=_ex)


@router.post(
    path="/templates",
    description="Create Aircraft template",
    status_code=status.HTTP_201_CREATED,
    response_model=DefaultResponse[List[None]],
    responses=build_responses(
        include={status.HTTP_201_CREATED, status.HTTP_500_INTERNAL_SERVER_ERROR}
    )
)
async def create_aircraft_template(request: Request, response: Response, _payload: Annotated[CreateAircraftTemplatesBody, Body()]):
    db_proxy: DBProxy = request.state.db_proxy

    async def db_query(session):
        return await query_create_template(session, _payload=_payload)

    try:
        cache_key = f"template:{_payload.template_name}"
        await db_proxy.update_and_cache(
            key=cache_key,
            db_name="powerplatform",
            update_func=db_query,
            ttl=60
        )

        return success_response(request=request, response=response, msg="Aircraft template created successfully",
                                status_code=status.HTTP_201_CREATED, data=[])

    except Exception as _ex:
        logger.error(f"Failed to create Aircraft template: {_ex}")
        return error_response(request=request, response=response, exc=_ex)


@router.get(
    path="/full",
    description="Get Aircrafts Full",
    status_code=status.HTTP_200_OK,
    response_model=DefaultResponse[List[AircraftSchemaFull]],
    responses=build_responses(
        include={status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_500_INTERNAL_SERVER_ERROR}
    )
)
async def get_aircrafts_full(request: Request, response: Response, _payload: Annotated[GetAircraftQuery, Query()]):
    db_proxy: DBProxy = request.state.db_proxy

    async def db_query(session):
        return await query_aircrafts(session, full=True, _payload=_payload)

    try:
        cache_key = cache_key_first_non_null(name="aircraft:full", data=_payload.model_dump(),
                                             keys=(
                                                 "template_id", "template_name", "aircraft_registration", "aircraft_id",
                                                 "airline_id", "airline_name", "aircraft_msn"),
                                             fallback="all")
        aircraft_data = await db_proxy.get_or_cache(
            key=cache_key,
            db_name="powerplatform",
            query_func=db_query,
            ttl=60
        )
        if len(aircraft_data) > 0:
            return success_response(request=request, response=response, data=aircraft_data,
                                    msg="Aircraft retrieved successfully")
        return warning_response(request=request, response=response, msg="Aircraft not found",
                                status_code=status.HTTP_404_NOT_FOUND)

    except ValueError:
        return warning_response(request=request, response=response, msg="Aircraft not found",
                                status_code=status.HTTP_404_NOT_FOUND)
    except Exception as _ex:
        logger.error(f"Failed to get Aircraft: {_ex}")
        return error_response(request=request, response=response, exc=_ex)


@router.get(
    path="/light",
    description="Get Aircrafts Light",
    status_code=status.HTTP_200_OK,
    response_model=DefaultResponse[List[AircraftSchemaLight]],
    responses=build_responses(
        include={status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_500_INTERNAL_SERVER_ERROR}
    )
)
async def get_aircrafts_light(request: Request, response: Response, _payload: Annotated[GetAircraftQuery, Query()]):
    db_proxy: DBProxy = request.state.db_proxy

    async def db_query(session):
        return await query_aircrafts(session, full=False, _payload=_payload)

    try:
        cache_key = cache_key_first_non_null(name="aircraft:light", data=_payload.model_dump(),
                                             keys=(
                                                 "template_id", "template_name", "aircraft_registration", "aircraft_id",
                                                 "airline_id", "airline_name", "aircraft_msn"),
                                             fallback="all")

        aircraft_data = await db_proxy.get_or_cache(
            key=cache_key,
            db_name="powerplatform",
            query_func=db_query,
            ttl=60
        )
        if len(aircraft_data) > 0:
            return success_response(request=request, response=response, data=aircraft_data,
                                    msg="Aircraft retrieved successfully")
        return warning_response(request=request, response=response, msg="Aircraft not found",
                                status_code=status.HTTP_404_NOT_FOUND)

    except ValueError:
        return warning_response(request=request, response=response, msg="Aircraft not found",
                                status_code=status.HTTP_404_NOT_FOUND)
    except Exception as _ex:
        logger.error(f"Failed to get Aircraft: {_ex}")
        return error_response(request=request, response=response, exc=_ex)


@router.post(
    path="/",
    description="Create Aircraft",
    status_code=status.HTTP_201_CREATED,
    response_model=DefaultResponse[List[None]],
    responses=build_responses(
        include={status.HTTP_201_CREATED, status.HTTP_500_INTERNAL_SERVER_ERROR}
    )
)
async def create_aircraft(request: Request, response: Response, _payload: Annotated[CreateUpdateAircraftBody, Query()]):
    db_proxy: DBProxy = request.state.db_proxy

    async def db_query(session):
        return await query_create_update_aircraft(session, _payload)

    try:
        cache_key = f"aircraft:{_payload.aircraft_registration}"
        await db_proxy.update_and_cache(
            key=cache_key,
            db_name="powerplatform",
            update_func=db_query,
            ttl=60
        )

        return success_response(request=request, response=response, msg="Aircraft created successfully",
                                status_code=status.HTTP_201_CREATED, data=[])

    except Exception as _ex:
        logger.error(f"Failed to create Aircraft: {_ex}")
        return error_response(request=request, response=response, exc=_ex)


@router.get(
    path="/engines/type",
    description="Get Engines Type",
    status_code=status.HTTP_200_OK,
    response_model=DefaultResponse[List[EngineTypeSchema]],
    responses=build_responses(
        include={status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_500_INTERNAL_SERVER_ERROR}
    )
)
async def get_engines_type(request: Request, response: Response, _payload: Annotated[GetEngineTypeQuery, Query()]):
    db_proxy: DBProxy = request.state.db_proxy

    async def db_query(session):
        return await query_get_engines_type(session, _payload)

    try:
        cache_key = cache_key_first_non_null(name="engine_type", data=_payload.model_dump(),
                                             keys=(
                                                 "aircraft_id", "engine_id", "engine_manufacture", "engine_type"),
                                             fallback="all")

        engine_data = await db_proxy.get_or_cache(
            key=cache_key,
            db_name="powerplatform",
            query_func=db_query,
            ttl=60
        )
        if len(engine_data) > 0:
            return success_response(request=request, response=response, data=engine_data,
                                    msg="Engine retrieved successfully")
        return warning_response(request=request, response=response, msg="Engine not found",
                                status_code=status.HTTP_404_NOT_FOUND)

    except ValueError:
        return warning_response(request=request, response=response, msg="Engine not found",
                                status_code=status.HTTP_404_NOT_FOUND)
    except Exception as _ex:
        logger.error(f"Failed to get Engine: {_ex}")
        return error_response(request=request, response=response, exc=_ex)


@router.get(
    path="/engines",
    description="Get Aircraft Engines",
    status_code=status.HTTP_200_OK,
    response_model=DefaultResponse[List[EngineSchema]],
    responses=build_responses(
        include={status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_500_INTERNAL_SERVER_ERROR}
    )
)
async def get_engines(request: Request, response: Response, _payload: Annotated[GetAircraftIDQuery, Query()]):
    db_proxy: DBProxy = request.state.db_proxy

    async def db_query(session):
        return await query_get_engines(session, _payload)

    try:
        cache_key = cache_key_first_non_null(name="engine", data=_payload.model_dump(),
                                             keys="aircraft_id",
                                             fallback="all")

        engine_data = await db_proxy.get_or_cache(
            key=cache_key,
            db_name="powerplatform",
            query_func=db_query,
            ttl=60
        )
        if len(engine_data) > 0:
            return success_response(request=request, response=response, data=engine_data,
                                    msg="Engine retrieved successfully")
        return warning_response(request=request, response=response, msg="Engine not found",
                                status_code=status.HTTP_404_NOT_FOUND)

    except ValueError:
        return warning_response(request=request, response=response, msg="Engine not found",
                                status_code=status.HTTP_404_NOT_FOUND)
    except Exception as _ex:
        logger.error(f"Failed to get Engine: {_ex}")
        return error_response(request=request, response=response, exc=_ex)


@router.get(
    path="/additional",
    description="Get Aircrafts additional information",
    status_code=status.HTTP_200_OK,
    response_model=DefaultResponse[List[AdditionalAircraftInfoSchema]],
    responses=build_responses(
        include={status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_500_INTERNAL_SERVER_ERROR}
    )
)
async def get_aircrafts_additional(request: Request, response: Response, _payload: Annotated[GetAircraftIDQuery, Query()]):
    payload = GetAircraftIDQuery(
        **_payload.model_dump()
    )

    db_proxy: DBProxy = request.state.db_proxy

    async def db_query(session):
        return await query_aircraft_additional(session, aircraft_id=payload.aircraft_id)

    try:
        cache_key = f"aircraft_additional:{payload.aircraft_id}"
        aircraft_data = await db_proxy.get_or_cache(
            key=cache_key,
            db_name="aixii_cirium",
            query_func=db_query,
            ttl=60
        )
        if len(aircraft_data) > 0:
            return success_response(request=request, response=response, data=aircraft_data,
                                    msg="Aircraft additional info retrieved successfully")
        return warning_response(request=request, response=response, msg="Aircraft not found",
                                status_code=status.HTTP_404_NOT_FOUND)

    except ValueError:
        return warning_response(request=request, response=response, msg="Aircraft not found",
                                status_code=status.HTTP_404_NOT_FOUND)
    except Exception as _ex:
        logger.error(f"Failed to get Aircraft additional info: {_ex}")
        return error_response(request=request, response=response, exc=_ex)
