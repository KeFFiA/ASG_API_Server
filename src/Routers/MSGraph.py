from typing import Optional, Annotated

from fastapi import APIRouter, Request, status, Path, Query
from fastapi.responses import JSONResponse

from Config import setup_logger, FILES_PATH
from Schemas import SuccessResponse, ErrorResponse, InviteUserSchema
from Schemas.Enums import service

logger = setup_logger(name="msgraph")

router = APIRouter(
    prefix="/msgraph",
    tags=[service.APITagsEnum.MSGRAPH],
)

MSGraphResponses = {
    201: {"model": SuccessResponse, "description": "Created"},
    500: {"model": ErrorResponse, "description": "Server error"},
}

@router.post("/invite_user/{filename}",
             description=f"Create user invitation process\nREQUIRE fileName of file with user data in '{FILES_PATH}' path, if posts without user data",
             status_code=201, responses=MSGraphResponses)
async def invite_user(
    request: Request,
    user_data: Annotated[InviteUserSchema, Query(description="User data if file not provided")],
    filename: Optional[str] = Path(description=f"Optional file name in '{FILES_PATH}'")
   ):

    ...