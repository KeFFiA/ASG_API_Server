from typing import Optional

from fastapi import Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from Schemas import DetailField, DefaultResponse


def success_response(*, request: Request, data: Optional[list | dict | BaseModel] = None, msg: str = "Success",
                     status_code: status = status.HTTP_200_OK, media_type: Optional[str] = None) -> JSONResponse:
    if isinstance(data, BaseModel):
        data = data.model_dump(mode="json")
    return JSONResponse(
        status_code=status_code,
        content=DefaultResponse(
            status_code=status_code,
            details=DetailField(msg=msg, correlationId=request.state.correlation_id),
            data=data
        ).model_dump(mode="json"),
        media_type=media_type
    )


def warning_response(*, request: Request, data: Optional[list | dict | BaseModel] = None,
                     exc: Optional[Exception] = None,
                     msg: Optional[str] = None,
                     status_code: status = status.HTTP_400_BAD_REQUEST,
                     media_type: Optional[str] = None) -> JSONResponse:
    if not exc and not msg:
        raise ValueError("exc or msg must be provided")
    if isinstance(data, BaseModel):
        data = data.model_dump(mode="json")
    if exc:
        return JSONResponse(
            status_code=status_code,
            content=DefaultResponse(
                status_code=status_code,
                details=DetailField(msg=f"{exc.__class__.__name__}: {str(exc)}",
                                    correlationId=request.state.correlation_id),
                data=data
            ).model_dump(mode="json"),
            media_type=media_type
        )
    else:
        return JSONResponse(
            status_code=status_code,
            content=DefaultResponse(
                status_code=status_code,
                details=DetailField(msg=msg,
                                    correlationId=request.state.correlation_id),
                data=data
            ).model_dump(mode="json"),
            media_type=media_type
        )


def error_response(*, request: Request, data: Optional[list | dict | BaseModel] = None, exc: Optional[Exception] = None,
                   msg: Optional[str] = None,
                   status_code: status = status.HTTP_500_INTERNAL_SERVER_ERROR,
                   media_type: Optional[str] = None) -> JSONResponse:
    if not exc and not msg:
        raise ValueError("exc or msg must be provided")
    if isinstance(data, BaseModel):
        data = data.model_dump(mode="json")
    if exc:
        return JSONResponse(
            status_code=status_code,
            content=DefaultResponse(
                status_code=status_code,
                details=DetailField(msg=f"{exc.__class__.__name__}: {str(exc)}",
                                    correlationId=request.state.correlation_id),
                data=data
            ).model_dump(mode="json"),
            media_type=media_type
        )
    else:
        return JSONResponse(
            status_code=status_code,
            content=DefaultResponse(
                status_code=status_code,
                details=DetailField(msg=msg,
                                    correlationId=request.state.correlation_id),
                data=data
            ).model_dump(mode="json"),
            media_type=media_type
        )
