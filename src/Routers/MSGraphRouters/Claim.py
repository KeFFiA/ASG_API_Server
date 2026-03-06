from typing import Annotated

from fastapi import status, Request, Query, Body

from Config import setup_logger, Router
from Schemas import DefaultResponse, ClaimsQuery, CreateClaimSchema
from Schemas.Enums import service
from Utils import DBProxy, success_response, error_response, warning_response
from .DBQueries.Claim import query_claims, query_create_claim

logger = setup_logger(name="msgraph_claims")

MSGraphResponses = {
    200: {"model": DefaultResponse, "description": "Success"},
    201: {"model": DefaultResponse, "description": "Created"},
    400: {"model": DefaultResponse, "description": "Bad Request"},
    404: {"model": DefaultResponse, "description": "Not found"},
    500: {"model": DefaultResponse, "description": "Server error"},
}

router = Router(
    prefix="/msgraph/claims",
    tags=[service.APITagsEnum.MSGRAPH],
    responses=MSGraphResponses,
)


@router.get(
    path="",
    description="Get claims",
    status_code=status.HTTP_200_OK,
    response_model=DefaultResponse,
)
async def get_claims(request: Request, _payload: Annotated[ClaimsQuery, Query()]):
    payload = ClaimsQuery(
        **_payload.model_dump()
    )

    if payload.claim_id and payload.user_id:
        return warning_response(request=request, msg="Only one of 'claim_id' or 'user_id' or nothing can be specified")

    db_proxy: DBProxy = request.app.state.db_proxy

    async def db_query(session):
        return await query_claims(session, claim_id=payload.claim_id, user_id=payload.user_id)

    try:
        if payload.user_id:
            cache_key = f"claims:{payload.user_id}"
        elif payload.claim_id:
            cache_key = f"claims:{payload.claim_id}"
        else:
            cache_key = "claims:all"
        airline_data = await db_proxy.get_or_cache(
            key=cache_key,
            db_name="powerplatform",
            query_func=db_query,
            ttl=60
        )
        if len(airline_data) > 0:
            return success_response(request=request, data=airline_data, msg="Claim(-s) retrieved successfully")
        return warning_response(request=request, msg="Claim(-s) not found", status_code=status.HTTP_404_NOT_FOUND)

    except ValueError:
        return warning_response(request=request, msg="Claim(-s) not found", status_code=status.HTTP_404_NOT_FOUND)
    except Exception as _ex:
        logger.error(f"Failed to get Claim(-s): {_ex}")
        return error_response(request=request, exc=_ex)


@router.post(
    path="",
    description="Create claim",
    status_code=status.HTTP_201_CREATED,
    response_model=DefaultResponse,
)
async def create_claim(request: Request, _payload: Annotated[CreateClaimSchema, Body()]):
    db_proxy: DBProxy = request.app.state.db_proxy

    try:
        async def db_query(session):
            return await query_create_claim(session, _payload)

        if _payload.user_id:
            cache_key = f"claims:{_payload.user_id}"
        else:
            cache_key = f"claims:{_payload.claim_id}"

        result = await db_proxy.update_and_cache(
            key=cache_key,
            db_name="powerplatform",
            update_func=db_query,
            ttl=60
        )
        return success_response(request=request, msg=f"Claim {result} successfully")

    except Exception as _ex:
        logger.error(f"Failed to create/update Claim: {_ex}")
        return error_response(request=request, exc=_ex)




