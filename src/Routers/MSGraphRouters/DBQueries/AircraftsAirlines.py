from base64 import b64decode
from datetime import date, datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func, cast, Date, literal, Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from Database import Airline, User, Asset, UserAirlineAccess, AircraftTemplate, Aircraft, CiriumAircrafts, \
    AircraftRevision, DatabaseClient, AircraftPolicy, Engine
from Schemas import AirlineSchema, UserSchemaShort, AircraftTemplateSchema, \
    AircraftSchema, GetAirlinesSchema, AdditionalAircraftInfoSchema, AdditionalAircraftInfoValuationSchema, \
    AircraftPolicySchema, CreateAircraftQuery, GetEnginesQuery, EnginesSchema
from Utils import map_asset


async def query_create_airline(session: AsyncSession, file_data: Optional[str], airline_name: str,
                               airline_icao: str, user_id: Optional[UUID]) -> bool:
    try:
        asset = None

        stmt = select(Airline).where(Airline.icao == airline_icao)
        existing = await session.execute(stmt)
        if existing.scalar_one_or_none():
            raise ValueError("Airline already exists")

        if file_data:
            header, encoded = file_data.split(",", 1)
            mime_type = header.split(";")[0].replace("data:", "")
            decoded_bytes = b64decode(encoded)

            asset = Asset(
                asset_name=f"{airline_name}",
                asset_description=None,
                mime_type=mime_type,
                base64=decoded_bytes
            )

        airline = Airline(
            airline_name=airline_name,
            icao=airline_icao,
            asset=asset
        )

        session.add(airline)
        await session.flush()

        if user_id:
            stmt = select(User.user_id).where(User.user_id == user_id)
            result = await session.execute(stmt)
            user_id_db = result.scalar_one_or_none()

            if not user_id_db:
                raise ValueError("User not found")

            session.add(
                UserAirlineAccess(
                    user_id=user_id_db,
                    airline_id=airline.id
                )
            )

        await session.commit()
        return True
    except Exception as _ex:
        raise _ex


async def map_airline_to_schema(airline) -> GetAirlinesSchema:
    users_list = [
        UserSchemaShort(
            user_id=user.user_id,
            user_mail=user.mail,
            user_displayname=user.display_name
        )
        for user in airline.users
    ]
    return GetAirlinesSchema(
        airline_id=airline.id,
        airline_name=airline.airline_name,
        airline_icao=airline.icao,
        asset=map_asset(asset=airline.asset),
        users=users_list
    ).model_dump(mode="json")


async def get_by_user_id(session: AsyncSession, user_id: UUID) -> list[GetAirlinesSchema]:
    stmt = (
        select(User)
        .options(
            selectinload(User.airlines)
            .selectinload(Airline.asset),
            selectinload(User.airlines)
            .selectinload(Airline.users)
        )
        .where(User.user_id == user_id)
    )

    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise ValueError("User not found")

    return [await map_airline_to_schema(airline) for airline in user.airlines]


async def get_by_airline(session: AsyncSession, airline_id: int | None = None,
                         airline_name: str | None = None) -> list[GetAirlinesSchema]:
    stmt = select(Airline).options(
        selectinload(Airline.asset),
        selectinload(Airline.users)
    )
    if airline_id:
        stmt = stmt.where(Airline.id == airline_id)
    if airline_name:
        stmt = stmt.where(Airline.airline_name == airline_name)

    result = await session.execute(stmt)
    airline = result.scalar_one_or_none()
    if not airline:
        raise ValueError("Airline not found")

    return [await map_airline_to_schema(airline)]


async def get_all_airlines(session: AsyncSession) -> list[GetAirlinesSchema]:
    stmt = (
        select(Airline)
        .options(
            selectinload(Airline.asset),
            selectinload(Airline.users)
        )
        .order_by(Airline.airline_name)
    )
    result = await session.execute(stmt)
    airlines = result.scalars().all()
    return [await map_airline_to_schema(airline) for airline in airlines]


async def query_airline(session: AsyncSession, airline_name: str | None = None,
                        airline_id: int | None = None,
                        user_id: UUID | None = None) -> list[GetAirlinesSchema]:
    if user_id:
        return await get_by_user_id(session, user_id)
    if airline_id or airline_name:
        return await get_by_airline(session, airline_id, airline_name)
    return await get_all_airlines(session)


async def query_templates(session: AsyncSession, template_name: Optional[str], template_id: Optional[int]) -> list[
    AircraftTemplateSchema]:
    stmt = (
        select(AircraftTemplate)
        .options(
            selectinload(AircraftTemplate.asset),
        )
        .order_by(AircraftTemplate.template_name)
    )

    if template_name is not None:
        template_name_clean = template_name.strip().lower()
        stmt = stmt.where(func.lower(AircraftTemplate.template_name) == literal(template_name_clean))

    if template_id is not None:
        stmt = stmt.where(AircraftTemplate.id == template_id)

    result = await session.execute(stmt)
    aircraft_templates = result.scalars().all()

    response = []

    for aircraft_template in aircraft_templates:
        response.append(
            AircraftTemplateSchema(
                template_id=aircraft_template.id,
                template_name=aircraft_template.template_name,
                asset=map_asset(asset=aircraft_template.asset)
            ).model_dump(mode="json")
        )

    return response


async def query_create_template(session: AsyncSession, template_name: str, file_data: Optional[str]):
    try:
        asset = None

        _stmt = select(AircraftTemplate).where(AircraftTemplate.template_name == template_name)
        existing = await session.execute(_stmt)

        if existing.scalar_one_or_none():
            raise ValueError("Template already exists")

        if file_data:
            header, encoded = file_data.split(",", 1)
            mime_type = header.split(";")[0].replace("data:", "")
            decoded_bytes = b64decode(encoded)

            asset = Asset(
                asset_name=f"{template_name}",
                asset_description=None,
                mime_type=mime_type,
                base64=decoded_bytes
            )

        template = AircraftTemplate(
            template_name=template_name,
            asset=asset
        )

        session.add(template)

        await session.commit()
        return True
    except Exception as _ex:
        raise _ex


async def query_aircrafts(session: AsyncSession, airline_id: Optional[int], airline_name: Optional[str],
                          template_id: Optional[int], template_name: Optional[str],
                          aircraft_registration: Optional[str],
                          aircraft_msn: Optional[int], aircraft_id: Optional[int]) -> list[AircraftSchema]:
    try:
        stmt = (
            select(Aircraft)
            .join(Aircraft.airline)
            .join(Aircraft.template)
            .join(Aircraft.engine)
            .options(
                selectinload(Aircraft.airline).selectinload(Airline.asset),
                selectinload(Aircraft.template).selectinload(AircraftTemplate.asset),
                selectinload(Aircraft.policy)
            )
            .order_by(Airline.airline_name)
        )

        if aircraft_registration:
            stmt = stmt.where(Aircraft.registration == aircraft_registration)
        if aircraft_msn:
            stmt = stmt.where(Aircraft.msn == aircraft_msn)
        if aircraft_id:
            stmt = stmt.where(Aircraft.id == aircraft_id)
        if airline_name:
            stmt = stmt.where(Airline.airline_name == airline_name)
        if airline_id:
            stmt = stmt.where(Airline.id == airline_id)
        if template_name:
            stmt = stmt.where(AircraftTemplate.template_name == template_name)
        if template_id:
            stmt = stmt.where(AircraftTemplate.id == template_id)

        result = await session.execute(stmt)
        aircrafts = result.scalars().unique().all()

        aircrafts_list = []

        for aircraft in aircrafts:
            policy_list = []
            for ac_policy in aircraft.policy:
                policy_list.append(
                    AircraftPolicySchema(
                        policy_id=ac_policy.id,
                        policy_from=ac_policy.policy_from,
                        policy_to=ac_policy.policy_to
                    )
                )

            aircrafts_list.append(AircraftSchema(
                aircraft_id=aircraft.id,
                registration=aircraft.registration,
                msn=aircraft.msn,
                policy=policy_list,
                agreed_value=aircraft.agreed_value,
                agreed_value_down_percent=aircraft.agreed_value_down_percent,
                agreed_value_down_absolute=aircraft.agreed_value_down_absolute,
                combined_single_limit=aircraft.combined_single_limit,
                hull_and_spares_excess=aircraft.hull_and_spares_excess,
                all_risks_deductible=aircraft.all_risks_deductible,
                lessee=aircraft.lessee,
                lessor=aircraft.lessor,
                engines_manufacture=aircraft.engine.engine_manufacture,
                engines_model=aircraft.engine.engine_model,
                number_of_engines=aircraft.number_of_engines,
                engine1_msn=aircraft.engine1_msn,
                engine2_msn=aircraft.engine2_msn,
                engine3_msn=aircraft.engine3_msn,
                engine4_msn=aircraft.engine4_msn,
                in_dashboard=aircraft.in_dashboard,
                status=aircraft.status,
                airline=AirlineSchema(
                    airline_id=aircraft.airline.id,
                    airline_name=aircraft.airline.airline_name,
                    airline_icao=aircraft.airline.icao,
                    asset=None
                ),
                template=AircraftTemplateSchema(
                    template_id=aircraft.template.id,
                    template_name=aircraft.template.template_name,
                    asset=None
                )
            ).model_dump(mode="json"))
        return aircrafts_list
    except Exception as _ex:
        raise _ex


async def query_aircraft_additional(session: AsyncSession, aircraft_id: int):
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
        reg_num, msn = sub_aircraft_result.one_or_none()

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
        try:
            _market_value = value.get("Indicative_Market_Value_USm") / 1000000
        except:
            _market_value = None
        valuation_list.append(
            AdditionalAircraftInfoValuationSchema(
                date=value.get("created_at").strftime("%d-%m-%Y"),
                market_value=_market_value
            )
        )

    return AdditionalAircraftInfoSchema(
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
    ).model_dump(mode="json")


async def query_get_engines(session: AsyncSession, _payload: GetEnginesQuery):
    payload = GetEnginesQuery(
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
    if payload.id:
        stmt = stmt.where(Engine.id == payload.id)

    result = await session.execute(stmt)
    engines = result.scalars().all()

    engines_list = []
    for engine in engines:
        engines_list.append(
            EnginesSchema(
                id=engine.id,
                engine_model=engine.engine_model,
                engine_manufacture=engine.engine_manufacture,
            ).model_dump(mode="json")
        )

    return engines_list


async def query_create_aircraft(session: AsyncSession, _payload: CreateAircraftQuery) -> bool:
    payload = CreateAircraftQuery(
        **_payload.model_dump()
    )

    airline = await session.get(Airline, payload.airline_id)
    if not airline:
        raise ValueError("Airline not found")

    template = await session.get(AircraftTemplate, payload.template_id)
    if not template:
        raise ValueError("Aircraft template not found")

    engine = None
    if payload.engine_id:
        engine = await session.get(Engine, payload.engine_id)
        if not engine:
            raise ValueError("Engine not found")

    if payload.policy_from:
        if not isinstance(payload.policy_from, date):
            payload.policy_from = datetime.fromisoformat(str(payload.policy_from)).date()

    if payload.policy_to:
        if not isinstance(payload.policy_to, date):
            payload.policy_to = datetime.fromisoformat(str(payload.policy_to)).date()

    aircraft = await session.get(Aircraft, payload.aircraft_id)

    if aircraft is None:
        aircraft = Aircraft(
            id=payload.aircraft_id,
            registration=payload.aircraft_registration,
            msn=payload.aircraft_msn,
            airline_id=payload.airline_id,
            template_id=payload.template_id,
            in_dashboard=payload.in_dashboard,
            status=payload.status,
            engine_id=payload.engine_id,
            number_of_engines=payload.number_of_engines,
            engine1_msn=payload.engine1_msn,
            engine2_msn=payload.engine2_msn,
            engine3_msn=payload.engine3_msn,
            engine4_msn=payload.engine4_msn,
            agreed_value=payload.agreed_value,
            agreed_value_down_absolute=payload.agreed_value_down_absolute,
            agreed_value_down_percent=payload.agreed_value_down_percent,
            combined_single_limit=payload.combined_single_limit,
            all_risks_deductible=payload.all_risks_deductible,
            hull_and_spares_excess=payload.hull_and_spares_excess,
            lessee=payload.lessee,
            lessor=payload.lessor,
        )

        if payload.policy_from or payload.policy_to:
            aircraft.policy.append(
                AircraftPolicy(
                    policy_from=payload.policy_from,
                    policy_to=payload.policy_to
                )
            )

        session.add(aircraft)

        return True

    # -------------------------
    # UPDATE AIRCRAFT
    # -------------------------
    aircraft.registration = payload.aircraft_registration
    aircraft.msn = payload.aircraft_msn
    aircraft.airline_id = payload.airline_id
    aircraft.template_id = payload.template_id
    aircraft.in_dashboard = payload.in_dashboard
    aircraft.status = payload.status
    aircraft.engine_id = payload.engine_id
    aircraft.number_of_engines = payload.number_of_engines
    aircraft.engine1_msn = payload.engine1_msn
    aircraft.engine2_msn = payload.engine2_msn
    aircraft.engine3_msn = payload.engine3_msn
    aircraft.engine4_msn = payload.engine4_msn
    aircraft.agreed_value = payload.agreed_value
    aircraft.agreed_value_down_absolute = payload.agreed_value_down_absolute
    aircraft.agreed_value_down_percent = payload.agreed_value_down_percent
    aircraft.combined_single_limit = payload.combined_single_limit
    aircraft.all_risks_deductible = payload.all_risks_deductible
    aircraft.hull_and_spares_excess = payload.hull_and_spares_excess
    aircraft.lessee = payload.lessee
    aircraft.lessor = payload.lessor

    # -------------------------
    # POLICY CHECK
    # -------------------------
    if payload.policy_from or payload.policy_to:

        stmt = select(AircraftPolicy).where(
            AircraftPolicy.aircraft_id == aircraft.id,
            AircraftPolicy.policy_from == payload.policy_from,
            AircraftPolicy.policy_to == payload.policy_to
        )

        result = await session.execute(stmt)
        policy = result.scalar_one_or_none()

        if policy is None:
            aircraft.policy.append(
                AircraftPolicy(
                    policy_from=payload.policy_from,
                    policy_to=payload.policy_to
                )
            )

    return True
