from typing import Annotated

from fastapi import APIRouter, status, Request, Query

from Config import setup_logger
from .DBQueries.Application import query_fonts
from Schemas import DefaultResponse, ApplicationSizeQuery
from Schemas.Enums import service
from Utils import DBProxy, success_response, warning_response, error_response

logger = setup_logger(name="msgraph_application")

MSGraphResponses = {
    200: {"model": DefaultResponse, "description": "Success"},
    400: {"model": DefaultResponse, "description": "Bad Request"},
    500: {"model": DefaultResponse, "description": "Server error"},
}

router = APIRouter(
    prefix="/msgraph/application",
    tags=[service.APITagsEnum.MSGRAPH],
    responses=MSGraphResponses,
)


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

    db_proxy: DBProxy = request.app.state.db_proxy

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
        else:
            return warning_response(request=request, data=fonts_data, msg="Fonts not found")

    except Exception as _ex:
        return error_response(request=request, exc=_ex)
