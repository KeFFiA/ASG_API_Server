from typing import Annotated, List, Optional

from fastapi import APIRouter, Request, status, Query
from sqlalchemy import select
from fastapi.responses import JSONResponse
from sqlalchemy.orm import selectinload

from Config import setup_logger
from Database import User, ApplicationAccess, UserAssignedLicenseLink
from Schemas import ErrorValidationResponse, ErrorResponse, SuccessDataResponse, DetailField
from Schemas.Enums import service
from Utils import DBProxy

logger = setup_logger(name="msgraph_users")

router = APIRouter(
    prefix="/msgraph",
    tags=[service.APITagsEnum.MSGRAPH],
    responses={422: {"model": ErrorValidationResponse}},
)


MSGraphResponses = {
    200: {"model": SuccessDataResponse, "description": "Success"},
    400: {"model": ErrorResponse, "description": "Bad Request"},
    500: {"model": ErrorResponse, "description": "Server error"},
}


async def query_all_users(session, user_id: Optional[str] = None) -> List[dict]:
    if user_id is None:
        result = await session.execute(
            select(User)
            .options(
                selectinload(User.assigned_licenses_links).selectinload(UserAssignedLicenseLink.license),
                selectinload(User.assigned_plans),
                selectinload(User.drives),
                selectinload(User.messages),
                selectinload(User.calendars),
                selectinload(User.photos),
                selectinload(User.contacts),
                selectinload(User.application_accesses).selectinload(ApplicationAccess.application)
            )
        )
    else:
        result = await session.execute(
            select(User)
            .options(
                selectinload(User.assigned_licenses_links).selectinload(UserAssignedLicenseLink.license),
                selectinload(User.assigned_plans),
                selectinload(User.drives),
                selectinload(User.messages),
                selectinload(User.calendars),
                selectinload(User.photos),
                selectinload(User.contacts),
                selectinload(User.application_accesses).selectinload(ApplicationAccess.application)
            )
            .where(User.user_id == user_id)
        )
    users: List[User] = result.scalars().all()

    users_data = []
    for u in users:
        if "ADMIN" in u.display_name.upper():
            continue
        users_data.append({
            "user_id": u.user_id,
            "display_name": u.display_name,
            "given_name": u.given_name,
            "surname": u.surname,
            "user_principal_name": u.user_principal_name,
            "account_enabled": u.account_enabled,
            "mail": u.mail,
            "mobile_phone": u.mobile_phone,
            "city": u.city,
            "country": u.country,
            "department": u.department,
            "job_title": u.job_title,
            "employee_id": u.employee_id,
            "employee_hire_date": u.employee_hire_date.isoformat() if u.employee_hire_date else None,
            "created_date_time": u.created_date_time.isoformat() if u.created_date_time else None,
            "manager_id": u.manager_id,
            "assigned_licenses": [
                {
                    "license_id": l.license_id,
                    "sku_id": l.sku_id,
                    "disabled_plans": l.disabled_plans
                } for l in u.assigned_licenses
            ],
            "assigned_plans": [
                {
                    "plan_id": p.plan_id,
                    "capability_status": p.capability_status,
                    "service": p.service
                } for p in u.assigned_plans
            ],
            "drives": [
                {
                    "drive_id": d.drive_id,
                    "drive_type": d.drive_type
                } for d in u.drives
            ],
            "messages": [
                {
                    "message_id": m.message_id,
                    "subject": m.subject,
                    "body_preview": m.body_preview
                } for m in u.messages
            ],
            "calendars": [
                {
                    "calendar_id": c.calendar_id,
                    "name": c.name
                } for c in u.calendars
            ],
            "photos": [
                {
                    "photo_id": p.photo_id,
                    "url": p.url
                } for p in u.photos
            ],
            "contacts": [
                {
                    "contact_id": c.contact_id,
                    "display_name": c.display_name,
                    "email": c.email
                } for c in u.contacts
            ],
            "application_accesses": [
                {
                    "application_id": a.application_id,
                    "application_name": a.application.application_name,
                    "rules": a.rules,
                    "main_access": a.main_access,
                    "super_admin": a.super_admin
                } for a in u.application_accesses
            ]
        })
    return users_data


@router.get(
    path="/users",
    description="Get users information",
    status_code=status.HTTP_200_OK,
    response_model=SuccessDataResponse
)
async def users(request: Request):
    db_proxy: DBProxy = request.app.state.db_proxy
    async def db_query(session):
        return await query_all_users(session)
    try:
        cache_key = "users:all"
        users_data = await db_proxy.get_or_cache(
            key=cache_key,
            db_name="powerplatform",
            query_func=db_query,
            ttl=60
        )

        if len(users_data) > 0:
            response = SuccessDataResponse(
                correlationId=request.state.correlation_id,
                code=status.HTTP_200_OK,
                detail=[DetailField(msg="Users retrieved successfully")],
                data=users_data
            )
            return JSONResponse(status_code=status.HTTP_200_OK, content=response.model_dump(mode="json"))
        else:
            response = SuccessDataResponse(
                correlationId=request.state.correlation_id,
                code=status.HTTP_200_OK,
                detail=[DetailField(msg="Users not found")],
                data=users_data
            )
            return JSONResponse(status_code=status.HTTP_200_OK, content=response.model_dump(mode="json"))

    except Exception as e:
        response = ErrorResponse(
            correlationId=request.state.correlation_id,
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=[DetailField(msg=f"{e.__class__.__name__}: {str(e)}")]
        )
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=response.model_dump(mode="json"))


@router.get(
    path="/users/{user_id}",
    description="Get user information",
    status_code=status.HTTP_200_OK,
    response_model=SuccessDataResponse
)
async def users(request: Request, user_id: str):
    db_proxy: DBProxy = request.app.state.db_proxy
    async def db_query(session):
        return await query_all_users(session, user_id)
    try:
        cache_key = f"users:{user_id}"
        user_data = await db_proxy.get_or_cache(
            key=cache_key,
            db_name="powerplatform",
            query_func=db_query,
            ttl=30
        )

        if len(user_data) > 0:
            response = SuccessDataResponse(
                correlationId=request.state.correlation_id,
                code=status.HTTP_200_OK,
                detail=[DetailField(msg="User retrieved successfully")],
                data=user_data
            )
            return JSONResponse(status_code=status.HTTP_200_OK, content=response.model_dump(mode="json"))
        else:
            response = SuccessDataResponse(
                correlationId=request.state.correlation_id,
                code=status.HTTP_200_OK,
                detail=[DetailField(msg="User not found")],
                data=user_data
            )
            return JSONResponse(status_code=status.HTTP_200_OK, content=response.model_dump(mode="json"))

    except Exception as e:
        response = ErrorResponse(
            correlationId=request.state.correlation_id,
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=[DetailField(msg=f"{e.__class__.__name__}: {str(e)}")]
        )
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=response.model_dump(mode="json"))
