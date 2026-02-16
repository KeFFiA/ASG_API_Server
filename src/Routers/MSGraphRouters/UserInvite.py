from typing import Annotated

from fastapi import APIRouter, Request, status, Query

from starlette.responses import JSONResponse

from msgraph.generated.models.o_data_errors.o_data_error import ODataError

from API.MSGraphAPI.Users import invite_guest_user
from Config import setup_logger
from Schemas import SuccessResponse, ErrorResponse, InviteUserSchema, InviteUserSchemaQuery, ErrorValidationResponse, \
    DetailField
from Schemas.Enums import service

logger = setup_logger(name="msgraph_invite_user")

router = APIRouter(
    prefix="/msgraph",
    tags=[service.APITagsEnum.MSGRAPH],
    responses={422: {"model": ErrorValidationResponse}},
)


MSGraphResponses = {
    201: {"model": SuccessResponse, "description": "Created"},
    400: {"model": ErrorResponse, "description": "Bad Request"},
    500: {"model": ErrorResponse, "description": "Server error"},
}


@router.post("/invite_user",
            description="Create user invitation process by user data",
            status_code=status.HTTP_201_CREATED, responses=MSGraphResponses)
async def invite_user(request: Request, user_data: Annotated[InviteUserSchemaQuery, Query()]):
    valid_data = InviteUserSchema(
        **user_data.model_dump()
    )
    try:
        result = await invite_guest_user(data=valid_data)
        if result is not None:
            success_response = SuccessResponse(
                correlationId=request.state.correlation_id,
                detail=[DetailField(msg="Invitation created")],
                code=status.HTTP_201_CREATED
            )

            return JSONResponse(status_code=status.HTTP_201_CREATED, content=success_response.model_dump(mode="json"))
    except ODataError as _ex:
        error_response = ErrorResponse(
            correlationId=request.state.correlation_id,
            code=_ex.response_status_code,
            detail=[DetailField(msg=str(_ex.error.message))],
        )
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=error_response.model_dump(mode="json"))





