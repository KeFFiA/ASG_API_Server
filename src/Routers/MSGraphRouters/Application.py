from typing import Annotated

from fastapi import status, Request, Query

from Config import setup_logger, Router
from Schemas import DefaultResponse, ApplicationSizeQuery, ApplicationIdQuery
from Schemas.Enums import service
from Utils import DBProxy, success_response, warning_response, error_response
from .DBQueries.Application import query_fonts, query_apps

logger = setup_logger(name="msgraph_application")

MSGraphResponses = {
    200: {"model": DefaultResponse, "description": "Success"},
    400: {"model": DefaultResponse, "description": "Bad Request"},
    404: {"model": DefaultResponse, "description": "Not found"},
    500: {"model": DefaultResponse, "description": "Server error"},
}

router = Router(
    prefix="/msgraph/application",
    tags=[service.APITagsEnum.MSGRAPH],
    responses=MSGraphResponses,
)


@router.get(
    path="",
    description="Get applications info",
    status_code=status.HTTP_200_OK,
    response_model=DefaultResponse
)
async def get_apps(request: Request, _payload: Annotated[ApplicationIdQuery, Query()]):
    payload = ApplicationIdQuery(
        **_payload.model_dump()
    )

    db_proxy: DBProxy = request.state.db_proxy

    async def db_query(session):
        return await query_apps(session, payload.application_id)

    try:
        if payload.application_id:
            cache_key = f"application:{payload.application_id}"
        else:
            cache_key = "application:all"

        apps_data = await db_proxy.get_or_cache(
            key=cache_key,
            db_name="powerplatform",
            query_func=db_query,
            ttl=600
        )

        if len(apps_data) > 0:
            return success_response(request=request, data=apps_data, msg="Application(-s) retrieved successfully")
        return warning_response(request=request, data=apps_data, msg="Application(-s) not found",
                                status_code=status.HTTP_404_NOT_FOUND)
    except Exception as _ex:
        logger.error(f"Failed to get Application(-s): {_ex}")
        return error_response(request=request, exc=_ex)


@router.get(
    path="/fonts",
    description="Get all fonts by screen size",
    status_code=status.HTTP_200_OK,
    response_model=DefaultResponse
)
async def get_fonts(request: Request, _payload: Annotated[ApplicationSizeQuery, Query()]):
    payload = ApplicationSizeQuery(
        **_payload.model_dump()
    )

    db_proxy: DBProxy = request.state.db_proxy

    async def db_query(session):
        return await query_fonts(session, payload.screen_size)

    try:
        cache_key = f"fonts:{payload.screen_size}"
        fonts_data = await db_proxy.get_or_cache(
            key=cache_key,
            db_name="powerplatform",
            query_func=db_query,
            ttl=60
        )

        if len(fonts_data) > 0:
            return success_response(request=request, data=fonts_data, msg="Fonts retrieved successfully")
        return warning_response(request=request, data=fonts_data, msg="Fonts not found",
                                status_code=status.HTTP_404_NOT_FOUND)
    except Exception as _ex:
        logger.error(f"Failed to get fonts: {_ex}")
        return error_response(request=request, exc=_ex)
