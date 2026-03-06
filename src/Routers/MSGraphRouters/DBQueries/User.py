import inspect
import sys
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload

from Database import User, Access
from Schemas import GetUserAccessResponseSchema, ApplicationAccessResponseSchema, RulesSchema, UserSchema


async def query_all_users(session, user_id: Optional[UUID] = None) -> List[UserSchema]:
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
    users: List[User] = result.scalars().all()

    users_data = []
    for u in users:
        if "ADMIN" in u.display_name.upper():
            continue

        users_data.append(
            UserSchema(
                user_id=u.user_id,
                display_name=u.display_name,
                given_name=u.given_name,
                surname=u.surname,
                user_principal_name=u.user_principal_name,
                account_enabled=u.account_enabled,
                mail=u.mail,
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
                    ApplicationAccessResponseSchema(
                        application_id=a.application_id,
                        rules=[
                            RulesSchema(
                                rule_id=rule.id,
                                rule_name=rule.rule_name,
                                rule_description=rule.rule_description
                            ) for rule in a.rules
                        ],
                        main_access=a.main_access,
                        super_admin=a.super_admin
                    ) for a in u.application_accesses
                ]
            ).model_dump(mode="json")
        )
    return users_data


async def query_user_access(session, user_id: UUID,
                            application_id: Optional[UUID] = None) -> GetUserAccessResponseSchema:
    if not user_id:
        raise ValueError("User ID required")
    try:
        stmt = (
            select(Access)
            .options(
                joinedload(Access.application),
                selectinload(Access.rules),
                joinedload(Access.user).load_only(User.super_admin)
            )
            .where(Access.user_id == user_id)
        )

        if application_id:
            stmt = stmt.where(Access.application_id == application_id)

        result = await session.execute(stmt)
        accesses = result.scalars().all()

        super_admin = False
        applications_list = []
        for access in accesses:
            if access.user.super_admin is True:
                super_admin = True
            applications_list.append(
                ApplicationAccessResponseSchema(
                    application_id=access.application.application_id,
                    rules=[
                        RulesSchema(rule_id=rule.id, rule_name=rule.rule_name, rule_description=rule.rule_description)
                        for rule in access.rules],
                    main_access=access.main_access
                )
            )

        return GetUserAccessResponseSchema(
            user_id=user_id,
            applications=applications_list,
            super_admin=super_admin
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
