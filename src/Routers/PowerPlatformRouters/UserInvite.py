from typing import Annotated, List

from fastapi import Request, status, Query, Response
from msgraph.generated.models.o_data_errors.o_data_error import ODataError

from API.MSGraphAPI.Users import invite_guest_user
from Config import setup_logger, Router
from Schemas import InviteUserSchema, InviteUserSchemaQuery, DefaultResponse
from Schemas.Enums import service
from Utils import success_response, warning_response
from Utils.ResponsesFunc import build_responses

logger = setup_logger(name="msgraph_invite_user")

router = Router(
    prefix="/msgraph",
    tags=[service.APITagsEnum.USERS],
)


@router.post(
    "/invite_user",
    description="Create user invitation process by user data",
    status_code=status.HTTP_201_CREATED,
    response_model=DefaultResponse[List[None]],
    responses=build_responses(
        include={status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST, status.HTTP_500_INTERNAL_SERVER_ERROR}
    )
)
async def invite_user(request: Request, response: Response, user_data: Annotated[InviteUserSchemaQuery, Query()]):
    valid_data = InviteUserSchema(
        **user_data.model_dump()
    )
    try:
        result = await invite_guest_user(data=valid_data)
        if result is not None:
            return success_response(request=request, response=response, msg="Invitation created",
                                    status_code=status.HTTP_201_CREATED, data=[])
    except ODataError as _ex:
        return warning_response(request=request, exc=_ex, response=response)
