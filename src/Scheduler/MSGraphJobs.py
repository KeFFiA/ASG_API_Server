from sqlalchemy.dialects.postgresql import insert

from Utils import performance_timer
from Database import DatabaseClient

@performance_timer
async def update_users_job():
    from Database.Models import User
    from API.MSGraphAPI.Users import get_users
    users = await get_users()
    client = DatabaseClient()
    async with client.session("powerplatform") as session:
        for user in users.value:
            print(user)
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

            await session.commit()



if __name__ == "__main__":
    import asyncio
    asyncio.run(update_users_job())
