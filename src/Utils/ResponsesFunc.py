from typing import Optional, Type, Any, TypeVar, get_origin

from fastapi import Request, status, Response
from pydantic import BaseModel

from Schemas import DetailField, DefaultResponse


T = TypeVar("T")

def build_responses(
    success_model: Type[Any],
    *,
    include: set[int],
    success_status: int,
):
    def _desc(code: int) -> str:
        return {
            status.HTTP_200_OK: "Success",
            status.HTTP_201_CREATED: "Created",
            status.HTTP_400_BAD_REQUEST: "Bad Request",
            status.HTTP_404_NOT_FOUND: "Not Found",
            status.HTTP_500_INTERNAL_SERVER_ERROR: "Server Error",
        }.get(code, "Response")

    def _empty_data_example(model):
        origin = get_origin(model)

        if origin in (list, set, tuple):
            return []

        if origin is dict:
            return {}

        return {}

    def success_example():
        return {
            "status_code": success_status,
            "details": {
                "msg": "string",
                "correlationId": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            },
            "data": _empty_data_example(success_model),
        }

    def error_example(status_code: int):
        return {
            "status_code": status_code,
            "details": {
                "msg": "string",
                "correlationId": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            },
            "data": [],
        }

    responses = {}

    for code in include:
        responses[code] = {
            "description": _desc(code),
            "content": {
                "application/json": {
                    "example": success_example() if code == success_status else error_example(code),
                }
            },
        }

    return responses


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
