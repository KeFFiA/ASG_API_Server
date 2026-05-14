from base64 import b64decode
from typing import List

from sqlalchemy import select, func, cast, Date, literal, Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from Database import Airline, Asset, AircraftTemplate, Aircraft, CiriumAircrafts, \
    AircraftRevision, DatabaseClient, Engine, AircraftEngine, AircraftManual, \
    AircraftEngineManual
from Scheduler.PowerPlatformJobs.Aircraft import update_create_aircraft_manual
from Schemas import AdditionalAircraftInfoSchema, AdditionalAircraftInfoValuationSchema, \
    PolicySchema, AircraftSchemaFull, EngineSchema, AirlineSchemaFull, TemplateSchemaFull, \
    AircraftSchemaLight, AirlineSchemaLight, TemplateSchemaLight, EngineTypeSchema, AircraftTechnicalDataSchema, \
    UpsertdelResponseSchema, UpsertdelStatusEnum
from Schemas.PowerPlatform.BodySchemas.AircraftSchemas import CreateUpdateAircraftBody, CreateAircraftTemplatesBody
from Schemas.PowerPlatform.QuerySchemas.AircraftSchemas import GetAircraftQuery, GetEngineTypeQuery, \
    GetAircraftTemplateQuery, GetAircraftIDQuery
from Utils import map_asset


async def query_templates(
        session: AsyncSession,
        full: bool,
        _payload: GetAircraftTemplateQuery
) -> List[TemplateSchemaFull] | List[TemplateSchemaLight]:
    payload = GetAircraftTemplateQuery(
        **_payload.model_dump()
    )

    stmt = select(AircraftTemplate).order_by(AircraftTemplate.template_name)

    if full:
        stmt = stmt.options(selectinload(AircraftTemplate.asset))

    if payload.template_name is not None:
        template_name_clean = payload.template_name.strip().lower()
        stmt = stmt.where(func.lower(AircraftTemplate.template_name) == literal(template_name_clean))

    if payload.template_id is not None:
        stmt = stmt.where(AircraftTemplate.id == payload.template_id)

    result = await session.execute(stmt)
    aircraft_templates = result.scalars().all()

    if full:
        response = [
            TemplateSchemaFull(
                template_id=t.id,
                template_name=t.template_name,
                asset=map_asset(t.asset)
            )
            for t in aircraft_templates
        ]
        return response

    response = [
        TemplateSchemaLight(
            template_id=t.id,
            template_name=t.template_name
        )
        for t in aircraft_templates
    ]

    return response


async def query_create_template(session: AsyncSession, _payload: CreateAircraftTemplatesBody):
    payload = CreateAircraftTemplatesBody(
        **_payload.model_dump()
    )

    asset = None

    _stmt = select(AircraftTemplate).where(AircraftTemplate.template_name == payload.template_name)
    existing = await session.execute(_stmt)

    if existing.scalar_one_or_none():
        raise ValueError("Template already exists")

    if payload.file_data:
        header, encoded = payload.file_data.split(",", 1)
        mime_type = header.split(";")[0].replace("data:", "")
        decoded_bytes = b64decode(encoded)

        asset = Asset(
            asset_name=f"{payload.template_name}",
            asset_description=None,
            mime_type=mime_type,
            base64=decoded_bytes
        )

    template = AircraftTemplate(
        template_name=payload.template_name,
        asset=asset
    )

    session.add(template)

    await session.commit()
    return True


async def query_aircrafts(
        session: AsyncSession, full: bool, _payload: GetAircraftQuery
) -> List[AircraftSchemaFull] | List[AircraftSchemaLight]:
    payload = GetAircraftQuery(
        **_payload.model_dump()
    )

    if full:
        stmt = (
            select(Aircraft)
            .join(Aircraft.airline)
            .join(Aircraft.template)
            .options(
                joinedload(Aircraft.airline).joinedload(Airline.asset),
                joinedload(Aircraft.template).joinedload(AircraftTemplate.asset),
                selectinload(Aircraft.policy),
                joinedload(Aircraft.technical_data),
                selectinload(Aircraft.engines)
                    .joinedload(AircraftEngine.engine),
                selectinload(Aircraft.lessee_lessors)
            )
            .order_by(Airline.airline_name)
        )
    else:
        stmt = (
            select(Aircraft)
            .join(Aircraft.airline)
            .join(Aircraft.template)
            .options(
                joinedload(Aircraft.airline),
                joinedload(Aircraft.template),
                joinedload(Aircraft.technical_data),
            )
            .order_by(Airline.airline_name)
        )

    if payload.aircraft_registration:
        stmt = stmt.where(Aircraft.registration == payload.aircraft_registration)
    if payload.aircraft_msn:
        stmt = stmt.where(Aircraft.msn == payload.aircraft_msn)
    if payload.aircraft_id:
        stmt = stmt.where(Aircraft.id == payload.aircraft_id)
    if payload.airline_name:
        stmt = stmt.where(Airline.airline_name == payload.airline_name)
    if payload.airline_id:
        stmt = stmt.where(Airline.id == payload.airline_id)
    if payload.template_name:
        stmt = stmt.where(AircraftTemplate.template_name == payload.template_name)
    if payload.template_id:
        stmt = stmt.where(AircraftTemplate.id == payload.template_id)

    result = await session.execute(stmt)
    aircrafts = result.scalars().unique().all()

    if full:
        response = []
        for a in aircrafts:
            active_lessee_lessor = next(
                (
                    item
                    for item in a.lessee_lessors
                    if item.active
                ),
                None
            )

            response.append(
                AircraftSchemaFull(
                    aircraft_id=a.id,
                    registration=a.registration,
                    msn=a.msn,
                    mtow=a.mtow,
                    policy=[
                        PolicySchema(
                            policy_id=p.id,
                            policy_from=p.policy_from,
                            policy_to=p.policy_to
                        )
                        for p in a.policy
                    ],
                    technical_data=(
                        AircraftTechnicalDataSchema(
                            in_dashboard=a.technical_data.in_dashboard,
                            status=a.technical_data.status,
                            data_source=a.technical_data.data_source,
                            av_fixed=a.technical_data.av_fixed
                        )
                        if a.technical_data else None
                    ),
                    agreed_value=a.agreed_value,
                    depreciation_rate=a.depreciation_rate,
                    depreciation_start_date=a.depreciation_start_date,
                    combined_single_limit=a.combined_single_limit,
                    hsl_deductible=a.hsl_deductible,
                    hd_deductible=a.hd_deductible,
                    lessee=active_lessee_lessor.lessee if active_lessee_lessor else None,
                    lessor=active_lessee_lessor.lessor if active_lessee_lessor else None,
                    engines=[
                        EngineSchema(
                            engine=EngineTypeSchema(
                                engine_id=engine.engine.id,
                                engine_manufacture=engine.engine.engine_manufacture,
                                engine_model=engine.engine.engine_model
                            ),
                            position=engine.position,
                            msn=engine.engine_msn
                        )
                        for engine in a.engines
                        if engine.engine
                    ] if a.engines else [],
                    airline=AirlineSchemaFull(
                        airline_id=a.airline.id,
                        airline_name=a.airline.airline_name,
                        airline_icao=a.airline.icao,
                        asset=map_asset(a.airline.asset)
                    ),
                    template=TemplateSchemaFull(
                        template_id=a.template.id,
                        template_name=a.template.template_name,
                        asset=map_asset(a.template.asset)
                    )
                )
            )

        return response

    response = [
        AircraftSchemaLight(
            aircraft_id=a.id,
            registration=a.registration,
            msn=a.msn,
            status=a.technical_data.status,
            airline=AirlineSchemaLight(
                airline_id=a.airline.id,
                airline_name=a.airline.airline_name,
                airline_icao=a.airline.icao
            ),
            template=TemplateSchemaLight(
                template_id=a.template.id,
                template_name=a.template.template_name
            )
        )
        for a in aircrafts
    ]

    return response


async def query_aircraft_additional(session: AsyncSession, aircraft_id: int) -> List[AdditionalAircraftInfoSchema]:
    db_client: DatabaseClient = DatabaseClient()
    async with db_client.session("powerplatform") as pp_session:
        sub_aircraft_stmt = (
            select(
                Aircraft.registration,
                Aircraft.msn
            ).where(
                Aircraft.id == aircraft_id
            )
        )

        sub_aircraft_result = await pp_session.execute(sub_aircraft_stmt)
        row = sub_aircraft_result.one_or_none()

        if not row:
            raise ValueError("Aircraft not found")
        reg_num, msn = row

    if reg_num is None:
        raise ValueError("Aircraft not found")

    msn = str(msn)

    last_revision_subq = select(
        func.max(AircraftRevision.id)
    ).scalar_subquery()

    stmt_aircraft = (
        select(
            CiriumAircrafts.Manufacturer,
            CiriumAircrafts.Aircraft_Sub_Series,
            CiriumAircrafts.Serial_Number,
            CiriumAircrafts.Age,
            CiriumAircrafts.Number_Of_Engines,
            CiriumAircrafts.Engine_Series,
            CiriumAircrafts.APU_Type,
            CiriumAircrafts.Number_of_Seats,
            CiriumAircrafts.Certified_MTOW_lbs,
            CiriumAircrafts.Indicative_Market_Lease_Rate_USm
        )
        .where(
            CiriumAircrafts.Registration == reg_num,
            CiriumAircrafts.Serial_Number == msn,
            CiriumAircrafts.revision_id == last_revision_subq
        )
    )

    stmt_value = (
        select(
            cast(CiriumAircrafts.created_at, Date),
            CiriumAircrafts.Indicative_Market_Value_USm,
        )
        .where(
            CiriumAircrafts.Registration == reg_num,
            CiriumAircrafts.Serial_Number == msn
        )
        .order_by(CiriumAircrafts.revision_id.asc())
    )

    result_aircraft = await session.execute(stmt_aircraft)
    aircraft = result_aircraft.mappings().first()

    if not aircraft:
        raise ValueError("Cirium aircraft not found")

    result_value = await session.execute(stmt_value)
    values = result_value.mappings().all()

    try:
        manufacturer = aircraft.get("Manufacturer", "Unknown")
    except:
        manufacturer = "Unknown"
    try:
        aircraft_series = aircraft.get("Aircraft_Sub_Series", "Unknown")
    except:
        aircraft_series = "Unknown"

    aircraft_type = f"{manufacturer} {aircraft_series}"

    valuation_list = []
    for value in values:
        _market_value = 0
        market_value = value.get("Indicative_Market_Value_USm")
        if market_value or market_value != 0:
            _market_value = market_value / 1_000_000

        valuation_list.append(
            AdditionalAircraftInfoValuationSchema(
                date=value.get("created_at").strftime("%d-%m-%Y"),
                market_value=_market_value
            )
        )

    data = AdditionalAircraftInfoSchema(
        aircraft=aircraft_type,
        msn=aircraft.get("Serial_Number", "Unknown"),
        age=aircraft.get("Age", "Unknown"),
        num_of_engines=aircraft.get("Number_Of_Engines", "Unknown"),
        engines_type=aircraft.get("Engine_Series", "Unknown"),
        apu_type=aircraft.get("APU_Type", "Unknown"),
        mtow=aircraft.get("Certified_MTOW_lbs", "Unknown"),
        num_of_seats=aircraft.get("Number_of_Seats", "Unknown"),
        lease_rate=aircraft.get("Indicative_Market_Lease_Rate_USm", "Unknown"),
        market_values=valuation_list
    )

    return [data]


async def query_get_engines_type(session: AsyncSession, _payload: GetEngineTypeQuery) -> List[EngineTypeSchema]:
    payload = GetEngineTypeQuery(
        **_payload.model_dump()
    )

    stmt = (
        Select(
            Engine
        ).order_by(
            Engine.engine_model
        ).distinct()
    )

    if payload.engine_manufacture:
        stmt = stmt.where(Engine.engine_manufacture == payload.engine_manufacture)
    if payload.engine_type:
        stmt = stmt.where(Engine.engine_model == payload.engine_type)
    if payload.engine_id:
        stmt = stmt.where(Engine.id == payload.engine_id)

    result = await session.execute(stmt)
    engines = result.scalars().all()

    return [
        EngineTypeSchema(
            engine_id=engine.id,
            engine_model=engine.engine_model,
            engine_manufacture=engine.engine_manufacture,
        )
        for engine in engines
    ]


async def query_get_engines(session: AsyncSession, _payload: GetAircraftIDQuery) -> List[EngineSchema]:
    payload = GetAircraftIDQuery(
        **_payload.model_dump()
    )

    stmt = (
        Select(
            AircraftEngine
        )
        .options(
            selectinload(AircraftEngine.engine)
        )
        .where(AircraftEngine.aircraft_id == payload.aircraft_id)
    )

    result = await session.execute(stmt)
    engines = result.scalars().all()

    return [
        EngineSchema(
            engine=EngineTypeSchema(
                engine_id=engine.engine.id,
                engine_manufacture=engine.engine.engine_manufacture,
                engine_model=engine.engine.engine_model
            ),
            position=engine.position,
            msn=engine.engine_msn
        )
        for engine in engines
        if engine.engine
    ]


async def query_create_update_aircraft(session: AsyncSession, _payload: CreateUpdateAircraftBody) -> List[
    UpsertdelResponseSchema]:
    payload = CreateUpdateAircraftBody(
        **_payload.model_dump()
    )

    stmt = (
        select(AircraftManual)
        .options(
            selectinload(AircraftManual.engines)
        )
        .where(
            AircraftManual.aircraft_id == payload.aircraft_id
        )
    )

    result = await session.execute(stmt)
    manual = result.scalar_one_or_none()

    status = [UpsertdelResponseSchema(status=UpsertdelStatusEnum.UPDATED)]

    # CREATE
    if manual is None:
        manual = AircraftManual(
            aircraft_id=payload.aircraft_id
        )
        session.add(manual)

        status = [UpsertdelResponseSchema(status=UpsertdelStatusEnum.CREATED)]

    # UPDATE MAIN DATA
    manual.registration = payload.aircraft_registration
    manual.msn = payload.aircraft_msn
    manual.airline_id = payload.airline_id
    manual.template_id = payload.template_id
    manual.mtow = payload.mtow

    # POLICY
    manual.policy_start = payload.policy_from
    manual.policy_end = payload.policy_to

    # LEASE
    manual.agreed_value = payload.agreed_value
    manual.depreciation_rate = payload.depreciation_rate
    manual.depreciation_start_date = payload.depreciation_start_date

    manual.combined_single_limit = payload.combined_single_limit
    manual.hsl_deductible = payload.hsl_deductible
    manual.hd_deductible = payload.hd_deductible

    # LESSOR / LESSEE
    manual.lessee = payload.lessee
    manual.lessor = payload.lessor

    await session.flush()

    manual.engines = [
        AircraftEngineManual(
            engine_id=e.engine_id,
            position=e.position,
            engine_msn=e.engine_msn
        )
        for e in payload.engines
    ]

    await session.commit()

    import asyncio
    loop = asyncio.get_running_loop()
    loop.create_task(
        update_create_aircraft_manual(manual.id)
    )

    return status
