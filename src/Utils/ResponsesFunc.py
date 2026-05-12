from typing import Optional, Type, Any, TypeVar, get_origin, Set

from fastapi import Request, status, Response
from pydantic import BaseModel

from Schemas import DetailField, DefaultResponse


T = TypeVar("T")

def build_responses(
    success_model: Type[Any],
    *,
    include: Set[int],
    success_status: int,
):
    def desc(code: int) -> str:
        return {
            200: "Success",
            201: "Created",
            202: "Accepted",
            400: "Bad Request",
            404: "Not Found",
            500: "Internal Server Error",
        }.get(code, "Response")

    return {
        code: {
            "description": desc(code)
        }
        for code in include
    }


def success_response(*, request: Request, response: Response, data: T, msg: str = "Success",
                     status_code: status = status.HTTP_200_OK) -> DefaultResponse[T]:
    response.status_code = status_code
    return DefaultResponse(
        status_code=status_code,
        details=DetailField(
            msg=msg,
            correlationId=request.state.correlation_id
        ),
        data=data
    )


def warning_response(*, request: Request, response: Response,
                     exc: Optional[Exception] = None,
                     msg: Optional[str] = None,
                     status_code: status = status.HTTP_400_BAD_REQUEST) -> DefaultResponse[T]:
    if not exc and not msg:
        raise ValueError("'exc' or 'msg' must be provided")
    response.status_code = status_code
    if exc:
        return DefaultResponse(
            status_code=status_code,
            details=DetailField(
                msg=f"{exc.__class__.__name__}: {str(exc)}",
                correlationId=request.state.correlation_id
            ),
            data=[]
        )
    else:
        return DefaultResponse(
            status_code=status_code,
            details=DetailField(
                msg=msg,
                correlationId=request.state.correlation_id
            ),
            data=[]
        )


def error_response(*, request: Request, response: Response,
                   exc: Optional[Exception] = None,
                   msg: Optional[str] = None,
                   status_code: status = status.HTTP_500_INTERNAL_SERVER_ERROR) -> DefaultResponse[T]:
    if not exc and not msg:
        raise ValueError("'exc' or 'msg' must be provided")
    response.status_code = status_code
    if exc:
        return DefaultResponse(
            status_code=status_code,
            details=DetailField(
                msg=f"{exc.__class__.__name__}: {str(exc)}",
                correlationId=request.state.correlation_id
            ),
            data=[]
        )
    else:
        return DefaultResponse(
            status_code=status_code,
            details=DetailField(
                msg=msg,
                correlationId=request.state.correlation_id
            ),
            data=[]
        )
