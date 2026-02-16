from sqlalchemy.dialects.postgresql import insert

from Utils import performance_timer
from Database import DatabaseClient

@performance_timer
async def update_users_job():
    from Database.Models import User, UserAssignedLicense, UserAssignedPlan, UserDrive, UserMessage, UserAssignedLicenseLink
    from API.MSGraphAPI.Users import get_users
    users = await get_users()
    client = DatabaseClient()
    async with client.session("powerplatform") as session:
        for user in users.value:
            # === User ===
            stmt_user = insert(User).values(
                user_id=user.id,
                display_name=user.display_name,
                given_name=user.given_name,
                surname=user.surname,
                user_principal_name=user.user_principal_name,
                account_enabled=user.account_enabled,
                mail=user.mail,
                mobile_phone=user.mobile_phone,
                city=user.city,
                country=user.country,
                department=user.department,
                job_title=user.job_title,
                employee_id=user.employee_id,
                employee_hire_date=user.employee_hire_date,
                created_date_time=user.created_date_time
            ).on_conflict_do_update(
                index_elements=['user_id'],
                set_={
                    'display_name': user.display_name,
                    'given_name': user.given_name,
                    'surname': user.surname,
                    'user_principal_name': user.user_principal_name,
                    'account_enabled': user.account_enabled,
                    'mail': user.mail,
                    'mobile_phone': user.mobile_phone,
                    'city': user.city,
                    'country': user.country,
                    'department': user.department,
                    'job_title': user.job_title,
                    'employee_id': user.employee_id,
                    'employee_hire_date': user.employee_hire_date,
                    'created_date_time': user.created_date_time,
                }
            )
            await session.execute(stmt_user)

            # === Assigned Licenses through ORM-class relation ===
            for license in getattr(user, "assigned_licenses", []) or []:
                stmt_license = insert(UserAssignedLicense).values(
                    license_id=license.license_id,
                    sku_id=license.sku_id,
                    disabled_plans=license.disabled_plans
                ).on_conflict_do_update(
                    index_elements=['license_id'],
                    set_={
                        'sku_id': license.sku_id,
                        'disabled_plans': license.disabled_plans,
                    }
                )
                await session.execute(stmt_license)

                # Relation user <-> license through ORM-class
                link = UserAssignedLicenseLink(user_id=user.id, license_id=license.license_id)
                session.add(link)

            # === Assigned Plans ===
            for plan in user.assigned_plans or []:
                stmt_plan = insert(UserAssignedPlan).values(
                    plan_id=plan.plan_id,
                    capability_status=plan.capability_status,
                    service=plan.service,
                    user_id=user.id
                ).on_conflict_do_update(
                    index_elements=['plan_id'],
                    set_={
                        'capability_status': plan.capability_status,
                        'service': plan.service,
                        'user_id': user.id,
                    }
                )
                await session.execute(stmt_plan)

            # === Drives ===
            for drive in user.drives or []:
                stmt_drive = insert(UserDrive).values(
                    drive_id=drive.drive_id,
                    drive_type=drive.drive_type,
                    user_id=user.id
                ).on_conflict_do_update(
                    index_elements=['drive_id'],
                    set_={
                        'drive_type': drive.drive_type,
                        'user_id': user.id,
                    }
                )
                await session.execute(stmt_drive)

            # === Messages ===
            for msg in user.messages or []:
                stmt_msg = insert(UserMessage).values(
                    message_id=msg.message_id,
                    subject=msg.subject,
                    body_preview=msg.body_preview,
                    user_id=user.id
                ).on_conflict_do_update(
                    index_elements=['message_id'],
                    set_={
                        'subject': msg.subject,
                        'body_preview': msg.body_preview,
                        'user_id': user.id,
                    }
                )
                await session.execute(stmt_msg)

            await session.commit()



if __name__ == "__main__":
    import asyncio
    asyncio.run(update_users_job())
