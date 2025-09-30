import json
import os
from typing import Annotated

from fastapi import APIRouter, Request, status, Path, BackgroundTasks, Query, Depends
from fastapi.responses import FileResponse
from pydantic import ValidationError
from starlette.responses import JSONResponse

from msgraph.generated.models.o_data_errors.o_data_error import ODataError

from API.MSGraphAPI.Users import invite_guest_user
from Config import setup_logger, FILES_PATH, RESPONSES_PATH
from Schemas import SuccessResponse, ErrorResponse, InviteUserSchema, InviteUserSchemaQuery, ErrorValidationResponse, \
    DetailField
from Schemas.Enums import service
from Utils import remove_file, validation_error_file

logger = setup_logger(name="msgraph")

router = APIRouter(
    prefix="/msgraph",
    tags=[service.APITagsEnum.MSGRAPH],
    responses={422: {"model": ErrorValidationResponse}},
)

file_description = f"""File name in '{FILES_PATH}'
!!ONLY JSON SCHEMA!!

Required fields: \n\n
user_email: Email of the user, who will get the invite\n\n
inviter_email: Email of the user, who send the invite\n\n
Optional fields:\n\n
user_displayName: Display name of the user, who will get the invite\n\n
user_type: Type of the created user. Guest or Member. Default is Guest.\n\n
custom_message: Message in invitation mail\n\n
expires_at: Expiration date of the access\n\n
redirect_url: URL where the user will be redirected after accept invitation
"""

MSGraphResponses = {
    201: {"model": SuccessResponse, "description": "Created"},
    400: {"model": ErrorResponse, "description": "Bad Request"},
    500: {"model": ErrorResponse, "description": "Server error"},
}

@router.get("/invite_user/{filename}",
            description=f"Create user invitation process by file with user data in '{FILES_PATH}' path, if posts without user data",
            summary="Invite User using file",
            status_code=status.HTTP_201_CREATED, responses=MSGraphResponses)
async def invite_user(
        request: Request,
        background_tasks: BackgroundTasks,
        filename: str = Path(description=file_description, title="JSON file"),
):
    if not filename.endswith(".json"):
        error_response = ErrorResponse(
            correlationId=request.state.correlation_id,
            detail=[DetailField(msg="File must have .json extension")],
            code=status.HTTP_400_BAD_REQUEST,
        )
        _filename = os.path.splitext(filename)[0] + ".json"
        filepath = Path(RESPONSES_PATH / _filename)
        filepath.write_text(error_response.model_dump_json(indent=4), encoding="utf-8")
        background_tasks.add_task(remove_file, filepath)
        background_tasks.add_task(remove_file, Path(FILES_PATH / filename))
        return FileResponse(status_code=status.HTTP_400_BAD_REQUEST,
                            path=filepath,
                            filename=_filename,
                            media_type="application/json",
                            background=background_tasks
                            )
    file_data = json.loads(Path(FILES_PATH / filename).read_text())
    try:
        valid_data = InviteUserSchema(
            **file_data
        )
        result = await invite_guest_user(data=valid_data)
        if result is not None:
            success_response = SuccessResponse(
                correlationId=request.state.correlation_id,
                detail=[DetailField(msg="Invitation created")],
                code=status.HTTP_201_CREATED
            )

            filepath = Path(RESPONSES_PATH / filename)
            filepath.write_text(success_response.model_dump_json(indent=4), encoding="utf-8")
            background_tasks.add_task(remove_file, filepath)
            background_tasks.add_task(remove_file, Path(FILES_PATH / filename))
            return FileResponse(status_code=status.HTTP_201_CREATED,
                                path=filepath,
                                filename=filename,
                                media_type="application/json",
                                background=background_tasks
                                )
    except ValidationError as e:
        return validation_error_file(filename=filename, exc=e, request=request, background_tasks=background_tasks)


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

