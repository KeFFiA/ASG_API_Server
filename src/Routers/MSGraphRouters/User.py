from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Request, status, Query

from Config import setup_logger
from Schemas import ApplicationIdQuery, \
    GetUserAccessResponseSchema, DefaultResponse
from Schemas.Enums import service
from Utils import DBProxy, success_response, warning_response, error_response
from .DBQueries.User import query_all_users, query_user_access

logger = setup_logger(name="msgraph_users")

MSGraphResponses = {
    200: {"model": DefaultResponse, "description": "Success"},
    400: {"model": DefaultResponse, "description": "Bad Request"},
    500: {"model": DefaultResponse, "description": "Server error"},
}

router = APIRouter(
    prefix="/msgraph/users",
    tags=[service.APITagsEnum.MSGRAPH],
    responses=MSGraphResponses,
)


@router.get(
    path="/",
    description="Get users information",
    status_code=status.HTTP_200_OK,
    response_model=DefaultResponse
)
async def users(request: Request):
    db_proxy: DBProxy = request.app.state.db_proxy

    async def db_query(session):
        return await query_all_users(session)

    try:
        cache_key = "users:all"
        users_data = await db_proxy.get_or_cache(
            key=cache_key,
            db_name="powerplatform",
            query_func=db_query,
            ttl=60
        )

        if len(users_data) > 0:
            return success_response(request=request, data=users_data, msg="Users retrieved successfully")
        else:
            return warning_response(request=request, data=users_data, msg="Users not found")

    except Exception as _ex:
        return error_response(request=request, exc=_ex)


@router.get(
    path="/{user_id}",
    description="Get user information",
    status_code=status.HTTP_200_OK,
    response_model=DefaultResponse
)
async def users(request: Request, user_id: UUID):
    db_proxy: DBProxy = request.app.state.db_proxy

    async def db_query(session):
        return await query_all_users(session, user_id)

    try:
        cache_key = f"users:{user_id}"
        user_data = await db_proxy.get_or_cache(
            key=cache_key,
            db_name="powerplatform",
            query_func=db_query,
            ttl=30
        )

        if len(user_data) > 0:
            return success_response(request=request, data=user_data, msg="User retrieved successfully")
        else:
            return warning_response(request=request, data=user_data, msg="User not found")

    except Exception as _ex:
        return error_response(request=request, exc=_ex)


@router.get(
    path="/{user_id}/access",
    description="Get user's access rules",
    status_code=status.HTTP_200_OK,
    response_model=DefaultResponse
)
async def users_access(request: Request, user_id: UUID, _payload: Annotated[ApplicationIdQuery, Query()]):
    payload = ApplicationIdQuery(
        **_payload.model_dump()
    )
    db_proxy: DBProxy = request.app.state.db_proxy

    async def db_query(session):
        return await query_user_access(session, user_id, payload.application_id)

    try:
        if payload.application_id is None:
            cache_key = f"user_access:{user_id}"
        else:
            cache_key = f"user_access:{user_id}|{payload.application_id}"
        user_data: GetUserAccessResponseSchema = await db_proxy.get_or_cache(
            key=cache_key,
            db_name="powerplatform",
            query_func=db_query,
            ttl=120
        )

        return success_response(request=request, data=user_data, msg="User's rules retrieved successfully")
    except Exception as _ex:
        logger.error(f"Failed to get user's access rules: {_ex}")
        return error_response(request=request, exc=_ex)
