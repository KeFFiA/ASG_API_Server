from typing import Annotated

from fastapi import Request, status, Query
from msgraph.generated.models.o_data_errors.o_data_error import ODataError

from API.MSGraphAPI.Users import invite_guest_user
from Config import setup_logger, Router
from Schemas import InviteUserSchema, InviteUserSchemaQuery, DefaultResponse
from Schemas.Enums import service
from Utils import success_response, warning_response

logger = setup_logger(name="msgraph_invite_user")

MSGraphResponses = {
    201: {"model": DefaultResponse, "description": "Created"},
    400: {"model": DefaultResponse, "description": "Bad Request"},
    500: {"model": DefaultResponse, "description": "Server error"},
}

router = Router(
    prefix="/msgraph",
    tags=[service.APITagsEnum.MSGRAPH],
    responses=MSGraphResponses,
)


@router.post("/invite_user",
             description="Create user invitation process by user data",
             status_code=status.HTTP_201_CREATED)
async def invite_user(request: Request, user_data: Annotated[InviteUserSchemaQuery, Query()]):
    valid_data = InviteUserSchema(
        **user_data.model_dump()
    )
    try:
        result = await invite_guest_user(data=valid_data)
        if result is not None:
            return success_response(request=request, msg="Invitation created", status_code=status.HTTP_201_CREATED)
    except ODataError as _ex:
        return warning_response(request=request, exc=_ex)
