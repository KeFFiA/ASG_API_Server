from typing import Annotated

from fastapi import APIRouter, status, Request, Query, Body

from Config import setup_logger
from Schemas import DefaultResponse, ApplicationFileQuery, ApplicationFileLoadBody
from Schemas.Enums import service
from Utils import DBProxy, success_response, error_response, warning_response
from .DBQueries.File import query_load_file, query_file

logger = setup_logger(name="msgraph_files")

MSGraphResponses = {
    200: {"model": DefaultResponse, "description": "Success"},
    201: {"model": DefaultResponse, "description": "Created"},
    400: {"model": DefaultResponse, "description": "Bad Request"},
    404: {"model": DefaultResponse, "description": "Not found"},
    500: {"model": DefaultResponse, "description": "Server error"},
}

router = APIRouter(
    prefix="/msgraph/files",
    tags=[service.APITagsEnum.MSGRAPH],
    responses=MSGraphResponses,
)


@router.post(
    path="",
    description="Upload file to Database",
    status_code=status.HTTP_201_CREATED,
    response_model=DefaultResponse,
)
async def upload_file(request: Request, _payload: Annotated[ApplicationFileLoadBody, Body()]):
    payload = ApplicationFileLoadBody(
        **_payload.model_dump()
    )

    db_proxy: DBProxy = request.app.state.db_proxy

    async def db_query(session):
        return await query_load_file(session, file_name=payload.file_name, file_description=payload.file_description,
                                     file_data=payload.file_data)

    try:
        cache_key = f"file:{payload.file_name}"
        await db_proxy.update_and_cache(
            key=cache_key,
            db_name="powerplatform",
            update_func=db_query,
            ttl=600
        )

        return success_response(request=request, msg="File uploaded successfully", status_code=status.HTTP_201_CREATED)

    except Exception as _ex:
        logger.error(f"Failed to upload file: {_ex}")
        return error_response(request=request, exc=_ex)


@router.get(
    path="",
    description="Get file from Database",
    status_code=status.HTTP_200_OK,
    response_model=DefaultResponse,
)
async def get_file(request: Request, _payload: Annotated[ApplicationFileQuery, Query()]):
    payload = ApplicationFileQuery(
        **_payload.model_dump()
    )

    if not payload.file_name and not payload.file_id:
        return warning_response(request=request, msg="Either 'file_name' or 'file_id' must be provided")
    if payload.file_name and payload.file_id:
        return warning_response(request=request, msg="Either 'file_name' or 'file_id' must be provided")

    db_proxy: DBProxy = request.app.state.db_proxy

    async def db_query(session):
        return await query_file(session, file_name=payload.file_name, file_id=payload.file_id)

    try:
        if payload.file_name:
            cache_key = f"file:{payload.file_name}"
        else:
            cache_key = f"file:{payload.file_id}"
        file_data = await db_proxy.get_or_cache(
            key=cache_key,
            db_name="powerplatform",
            query_func=db_query,
            ttl=600
        )
        if file_data.get("file_data"):
            return success_response(request=request, data=file_data, msg="File retrieved successfully")
        return warning_response(request=request, msg="File not found", status_code=status.HTTP_404_NOT_FOUND)
    except Exception as _ex:
        logger.error(f"Failed to get file: {_ex}")
        return error_response(request=request, exc=_ex)
