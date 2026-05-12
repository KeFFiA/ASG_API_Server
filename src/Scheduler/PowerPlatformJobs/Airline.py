from sqlalchemy import select

from Database import DatabaseClient, Airline, Airlines


async def sync_airlines():
    client: DatabaseClient = DatabaseClient()

    stmt = (
        select(Airlines.airline_name, Airlines.icao)
    )
    async with client.session("main") as main_session:
        result = await main_session.execute(stmt)
        airlines = result.all()


    existing_stmt = (
        select(Airline.airline_name)
    )
    async with client.session('powerplatform') as pp_session:
        existing_result = await pp_session.execute(existing_stmt)
        existing_airlines = set(existing_result.scalars().all())

        new_airlines = []
        for airline_name, airline_icao in airlines:
            if airline_name not in existing_airlines:
                new_airlines.append(
                    Airline(
                        airline_name=airline_name,
                        icao=airline_icao
                    )
                )

        pp_session.add_all(new_airlines)

        await pp_session.commit()


if __name__ == '__main__':
    import asyncio
    asyncio.run(sync_airlines())
