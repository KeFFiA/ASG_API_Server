from typing import Sequence, Optional, final, Set

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from Database import DatabaseClient, ASGAircrafts, Aircraft, Airline, Engine, AircraftTemplate, AircraftEngine, \
    AircraftTechnicalData, AircraftLesseeLessor, AircraftPolicy, CiriumAircrafts
from Schemas import AircraftInsuredStatusEnum, EnginePositionEnum
from Schemas.Enums import AircraftDataSourceEnum


async def load_references(session: AsyncSession) -> dict:
    return {
        "airlines": {
            a.airline_name: a
            for a in (
                await session.execute(select(Airline))
            ).scalars()
        },
        "engines": {
            e.engine_model: e
            for e in (
                await session.execute(select(Engine))
            ).scalars()
        },
        "templates": {
            t.template_name: t
            for t in (
                await session.execute(select(AircraftTemplate))
            ).scalars()
        },
    }

async def load_lessee_lessors(session: AsyncSession, aircraft_id: Optional[int] = None) -> dict:
    return {
        "lessee_lessors": {
            (l.lessee, l.lessor): l
            for l in (
                await session.execute(
                    select(AircraftLesseeLessor).where(AircraftLesseeLessor.aircraft_id == aircraft_id))
            ).scalars()
        }
    }

def get_engine_positions(number: int) -> Set[EnginePositionEnum]:
    if number == 1:
        return {EnginePositionEnum.NOSE}
    if number == 2:
        return {EnginePositionEnum.LEFT1, EnginePositionEnum.RIGHT1}
    if number == 3:
        return {EnginePositionEnum.LEFT1, EnginePositionEnum.RIGHT1, EnginePositionEnum.TAIL}
    if number == 4:
        return {EnginePositionEnum.LEFT1, EnginePositionEnum.RIGHT1, EnginePositionEnum.LEFT2, EnginePositionEnum.RIGHT2}
    raise ValueError(f"Invalid engine position number: {number}")



async def update_aircrafts():
    client: DatabaseClient = DatabaseClient()

    async with client.session("cirium") as cirium_session:
        cirium_stmt = select(ASGAircrafts).order_by(ASGAircrafts.Airline.desc())

        result = await cirium_session.execute(cirium_stmt)

        cirium_aircrafts: Sequence[ASGAircrafts] = result.scalars().all()

        async with client.session("powerplatform") as pp_session:
            stmt = (
                select(Aircraft)
                .options(
                    joinedload(Aircraft.technical_data),
                    joinedload(Aircraft.airline),
                    joinedload(Aircraft.template),

                    selectinload(Aircraft.engines)
                    .joinedload(AircraftEngine.engine),

                    selectinload(Aircraft.lessee_lessors),
                    selectinload(Aircraft.policy),
                )
            )

            result = await pp_session.execute(stmt)

            pp_aircrafts = {
                a.msn: a
                for a in result.scalars().unique().all()
            }

            refs = await load_references(pp_session)

            for cirium_aircraft in cirium_aircrafts:
                pp_aircraft = pp_aircrafts.get(int(cirium_aircraft.Serial_Number))

                if not pp_aircraft:
                    pp_aircraft = Aircraft(
                        registration=cirium_aircraft.Registration,
                        msn=int(cirium_aircraft.Serial_Number),
                    )

                    pp_aircraft.engines = []
                    pp_aircraft.lessee_lessors = []
                    pp_aircraft.engines = []

                    pp_aircraft.technical_data = AircraftTechnicalData(
                        data_source=AircraftDataSourceEnum.CIRIUM,
                        data_source_row_id=cirium_aircraft.id,
                        status=AircraftInsuredStatusEnum.INSURED,
                        av_fixed=True,
                        in_dashboard=True
                    )

                    pp_session.add(pp_aircraft)

                technical_data: AircraftTechnicalData = pp_aircraft.technical_data

                if technical_data and technical_data.data_source != AircraftDataSourceEnum.CIRIUM:
                    continue

                airline: Optional[Airline] = refs.get("airlines", {}).get(cirium_aircraft.Airline, None)
                if airline:
                    pp_aircraft.airline = airline

                template: Optional[AircraftTemplate] = refs.get("templates", {}).get(f"{cirium_aircraft.Manufacturer} {cirium_aircraft.Series}", None)
                if template:
                    pp_aircraft.template = template
                else:
                    print(f"{cirium_aircraft.Manufacturer} {cirium_aircraft.Series}")

                engine: Engine = refs.get("engines").get(cirium_aircraft.Engine_Master_Series)

                engine_positions = get_engine_positions(cirium_aircraft.Number_Of_Engines if cirium_aircraft.Number_Of_Engines else 2)

                aircraft_engines = []
                for engine_position in engine_positions:
                    aircraft_engines.append(
                        AircraftEngine(
                            aircraft=pp_aircraft,
                            engine=engine,
                            position=engine_position,
                        )
                    )

                pp_aircraft.engines = aircraft_engines

                lessee_lessor = next(
                    (
                        item
                        for item in pp_aircraft.lessee_lessors
                        if item.lessee == cirium_aircraft.Airline
                           and item.lessor == cirium_aircraft.Operational_Lessor
                    ),
                    None
                )

                if not lessee_lessor:
                    for item in pp_aircraft.lessee_lessors:
                        item.active = False

                    pp_aircraft.lessee_lessors.append(
                        AircraftLesseeLessor(
                            lessee=cirium_aircraft.Airline,
                            lessor=cirium_aircraft.Operational_Lessor,
                            active=True,
                        )
                    )
                else:
                    lessee_lessor.active = True

                pp_aircraft.mtow = round((cirium_aircraft.Operating_MTOW_lbs or 0) * 0.45359237)
                pp_aircraft.agreed_value_result = cirium_aircraft.Indicative_Market_Value_USm

            await pp_session.commit()


async def update_aircraft_templates():
    client: DatabaseClient = DatabaseClient()

    stmt = (
        select(CiriumAircrafts.Manufacturer, CiriumAircrafts.Series)
        .distinct()
    )

    async with client.session('cirium') as cirium_session:
        cirium_result = await cirium_session.execute(stmt)
        _cirium_templates = cirium_result.all()

    cirium_templates = []
    for manufacturer, series in _cirium_templates:
        cirium_templates.append(f"{manufacturer} {series}")

    existing_stmt = (
        select(AircraftTemplate.template_name)
    )

    async with client.session('powerplatform') as pp_session:
        pp_result = await pp_session.execute(existing_stmt)
        existing_templates = pp_result.scalars().all()

        new_templates = []
        for template in cirium_templates:
            if template not in existing_templates:
                new_templates.append(
                    AircraftTemplate(
                        template_name=template,
                    )
                )

        pp_session.add_all(new_templates)

        await pp_session.commit()


if __name__ == "__main__":
    import asyncio
    asyncio.run(update_aircrafts())
    # asyncio.run(update_aircraft_templates())
