import inspect
import sys
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload

from Database import User, ApplicationAccess
from Schemas import GetUserAccessResponseSchema, ApplicationAccessResponseSchema, RulesSchema


async def query_all_users(session, user_id: Optional[UUID] = None) -> List[dict]:
    if user_id is None:
        result = await session.execute(
            select(User)
            .options(
                selectinload(User.application_accesses).selectinload(ApplicationAccess.application)
            )
        )
    else:
        result = await session.execute(
            select(User)
            .options(
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
            "user_id": str(u.user_id),
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
            "manager_id": str(u.manager_id),
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


async def query_user_access(session, user_id: UUID,
                            application_id: Optional[UUID] = None) -> GetUserAccessResponseSchema:
    if not user_id:
        raise ValueError("User ID required")
    try:
        stmt = (
            select(ApplicationAccess)
            .options(
                joinedload(ApplicationAccess.application),
                selectinload(ApplicationAccess.rules)
            )
            .where(ApplicationAccess.user_id == user_id)
        )

        if application_id:
            stmt = stmt.where(ApplicationAccess.application_id == application_id)

        result = await session.execute(stmt)
        accesses = result.scalars().all()

        applications_list = []
        for access in accesses:
            applications_list.append(
                ApplicationAccessResponseSchema(
                    application_id=access.application.application_id,
                    rules=[
                        RulesSchema(rule_id=rule.id, rule_name=rule.rule_name, rule_description=rule.rule_description)
                        for rule in access.rules],
                    main_access=access.main_access,
                    super_admin=access.super_admin
                )
            )

        return GetUserAccessResponseSchema(
            user_id=user_id,
            applications=applications_list
        ).model_dump(mode="json")
    except Exception as _ex:
        raise _ex


_current_module = sys.modules[__name__]

__all__ = [
    name
    for name, obj in globals().items()
    if
    (inspect.isclass(obj) or inspect.isfunction(obj) or inspect.isasyncgenfunction(obj)) and obj.__module__ == __name__
]
