import asyncio

from sqlalchemy import select, inspect, or_
from sqlalchemy.dialects.postgresql import insert

from Database.Models import Airlines, CiriumAircrafts, ASGAircrafts, Registrations
from Database import DatabaseClient
from Config import setup_logger
from Utils import performance_timer

logger = setup_logger("registration_updater")

EXCLUDED_COLUMNS = {
    "id",
    "revision_id",
    "created_at",
    "updated_at",
}

EXCLUDED_STATUSES = ["Cancelled", "On order", "Retired", "Written off"]



async def regs_updater(client):
    async with client.session("cirium") as cirium_session:
        stmt = (
            select(ASGAircrafts.Registration, ASGAircrafts.Serial_Number, ASGAircrafts.Manufacturer, ASGAircrafts.Aircraft_Sub_Series)
        )
        results = await cirium_session.execute(stmt)

    async with client.session("main") as main_session:
        for row in results:
            ac_type = row.Manufacturer + " " + row.Aircraft_Sub_Series

            insert_stmt = insert(Registrations).values(
                reg=row.Registration,
                msn=row.Serial_Number,
                aircraft_type=ac_type,
                indashboard=True,
                status="Insured",
            )

            stmt = insert_stmt.on_conflict_do_update(
                index_elements=[Registrations.msn],
                set_={
                    "reg": insert_stmt.excluded.reg,
                    "msn": insert_stmt.excluded.msn,
                    "aircraft_type": insert_stmt.excluded.aircraft_type,
                    "indashboard": insert_stmt.excluded.indashboard,
                    "status": insert_stmt.excluded.status,
                }
            )

            await main_session.execute(stmt)



@performance_timer
async def asg_regs_updater():
    client = DatabaseClient()
    logger.info("Starting query")
    async with client.session("main") as main_session:
        stmt = (
            select(Airlines.airline_name)
        )
        result = await main_session.execute(stmt)
        airlines = result.scalars().all()

    mapper = inspect(CiriumAircrafts)

    columns = [
        column
        for column in mapper.columns
        if column.key not in EXCLUDED_COLUMNS
    ]

    filters = []
    for company in airlines:
        pattern = f"%{company}%"
        filters.extend([
            CiriumAircrafts.Operator.ilike(pattern),
            CiriumAircrafts.Sub_Lessor.ilike(pattern),
            CiriumAircrafts.Owner.ilike(pattern),
        ])

    async with client.session("cirium") as cirium_session:
        select_stmt = (
            select(*columns)
            .where(
                or_(*filters),
                CiriumAircrafts.Registration.isnot(None),
                ~CiriumAircrafts.Status.in_(EXCLUDED_STATUSES)

            )
            .distinct()
        )

        insert_stmt = (
            insert(ASGAircrafts)
            .from_select(
                [col.name for col in columns],
                select_stmt
            )
            .on_conflict_do_nothing()
        )

        await cirium_session.execute(insert_stmt)
        await cirium_session.commit()

    await regs_updater(client=client)
    logger.info("Query completed")



if __name__ == "__main__":
    asyncio.run(asg_regs_updater())
