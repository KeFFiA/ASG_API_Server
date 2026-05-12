import inspect
import sys
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from Database import User, Access
from Schemas.PowerPlatform.DefaultSchemas import ApplicationAccessSchema, RuleSchema
from Schemas.PowerPlatform.QuerySchemas.ApplicationSchemas import GetApplicationIdQuery
from Schemas.PowerPlatform.UserSchemas import UserSchemaFull, UserSchemaLight, UserAccessSchema


async def query_users(session: AsyncSession, full: bool, user_id: Optional[UUID] = None) -> List[UserSchemaFull] | List[UserSchemaLight]:
    if user_id is None:
        result = await session.execute(
            select(User)
            .options(
                selectinload(User.application_accesses).selectinload(Access.application)
            )
        )
    else:
        result = await session.execute(
            select(User)
            .options(
                selectinload(User.application_accesses).selectinload(Access.application)
            )
            .where(User.user_id == user_id)
        )
    users = result.scalars().all()

    if full:
        response: List[UserSchemaFull] = [
            UserSchemaFull(
                user_id=u.user_id,
                user_displayname=u.display_name,
                given_name=u.given_name,
                surname=u.surname,
                user_principal_name=u.user_principal_name,
                account_enabled=u.account_enabled,
                user_mail=u.mail,
                mobile_phone=u.mobile_phone,
                city=u.city,
                country=u.country,
                department=u.department,
                job_title=u.job_title,
                employee_id=u.employee_id,
                employee_hire_date=u.employee_hire_date.isoformat() if u.employee_hire_date else None,
                created_date_time=u.created_date_time.isoformat() if u.created_date_time else None,
                manager_id=u.manager_id,
                application_accesses=[
                    ApplicationAccessSchema(
                        application_id=a.application_id,
                        rules=[
                            RuleSchema(
                                rule_id=rule.id,
                                rule_name=rule.rule_name,
                                rule_description=rule.rule_description
                            ) for rule in a.rules
                        ],
                        main_access=a.main_access
                    ) for a in u.application_accesses
                ]
            )
            for u in users if "ADMIN" not in u.display_name.upper()
        ]
        return response
    else:
        response: List[UserSchemaLight] = [
            UserSchemaLight(
                user_id=u.user_id,
                user_displayname=u.display_name,
                user_mail=u.mail
            )
            for u in users if "ADMIN" not in u.display_name.upper()
        ]
        return response


async def query_user_access(session: AsyncSession, user_id: UUID, _payload: GetApplicationIdQuery) -> List[UserAccessSchema]:
    payload = GetApplicationIdQuery(
        **_payload.model_dump()
    )

    try:
        stmt = (
            select(Access)
            .options(
                selectinload(Access.application),
                selectinload(Access.rules),
                selectinload(Access.user)
            )
            .where(Access.user_id == user_id)
        )

        if payload.application_id:
            stmt = stmt.where(Access.application_id == payload.application_id)

        result = await session.execute(stmt)
        accesses = result.scalars().all()

        super_admin = False
        for access in accesses:
            if access.user.super_admin is True:
                super_admin = True
        user = [
            UserSchemaLight(
                user_id=access.user.user_id,
                user_displayname=access.user.display_name,
                user_mail=access.user.mail
            )
            for access in accesses
        ]
        applications_list = [
            ApplicationAccessSchema(
                application_id=access.application.application_id,
                rules=[
                    RuleSchema(rule_id=rule.id, rule_name=rule.rule_name, rule_description=rule.rule_description)
                    for rule in access.rules],
                main_access=access.main_access
            )
            for access in accesses
        ]

        response = UserAccessSchema(
            user=user[0],
            super_admin=super_admin,
            applications=applications_list
        )
        return [response]
    except Exception as _ex:
        raise _ex


_current_module = sys.modules[__name__]

__all__ = [
    name
    for name, obj in globals().items()
    if
    (inspect.isclass(obj) or inspect.isfunction(obj) or inspect.isasyncgenfunction(obj)) and obj.__module__ == __name__
]
