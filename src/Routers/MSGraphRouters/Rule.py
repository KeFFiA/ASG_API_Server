from typing import Optional
from uuid import UUID

from fastapi import APIRouter, status, Request

from Config import setup_logger
from .DBQueries.Rule import query_all_rules
from Schemas import DefaultResponse
from Schemas.Enums import service
from Utils import DBProxy, success_response, warning_response, error_response

logger = setup_logger(name="msgraph_rules")

MSGraphResponses = {
    200: {"model": DefaultResponse, "description": "Success"},
    400: {"model": DefaultResponse, "description": "Bad Request"},
    500: {"model": DefaultResponse, "description": "Server error"},
}

router = APIRouter(
    prefix="/msgraph",
    tags=[service.APITagsEnum.MSGRAPH],
    responses=MSGraphResponses,
)

@router.get(
    path="/rules",
    description="Get all rules",
    status_code=status.HTTP_200_OK,
    response_model=DefaultResponse
)
async def get_rules(request: Request):
    db_proxy: DBProxy = request.app.state.db_proxy

    async def db_query(session):
        return await query_all_rules(session)

    try:
        cache_key = "rules:all"
        rules_data = await db_proxy.get_or_cache(
            key=cache_key,
            db_name="powerplatform",
            query_func=db_query,
            ttl=60
        )

        if len(rules_data) > 0:
            return success_response(request=request, data=rules_data, msg="Rules retrieved successfully")
        else:
            return warning_response(request=request, data=rules_data, msg="Rules not found")

    except Exception as _ex:
        return error_response(request=request, exc=_ex)