from base64 import b64decode, b64encode
from datetime import date
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from Database import Airline, User, ApplicationAsset, UserAirlineAccess, AircraftTemplate, Aircraft
from Schemas import AirlineSchema, AirlinesSchemaByUser, UserSchemaShort, AirlinesSchemaUsers, GetFileResponseSchema, \
    AircraftTemplateSchema, AircraftSchema


def map_asset(asset: ApplicationAsset | None) -> GetFileResponseSchema | None:
    if not asset:
        return None

    encoded = b64encode(asset.base64).decode()
    data_uri = f"data:{asset.mime_type};base64,{encoded}"

    return GetFileResponseSchema(
        file_name=asset.asset_name,
        file_description=asset.asset_description,
        file_data=data_uri
    )


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

            asset = ApplicationAsset(
                asset_name=f"{airline_name}-LOGO",
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


async def get_by_user_id(
        session: AsyncSession,
        user_id: UUID
) -> AirlinesSchemaByUser:
    stmt = (
        select(User)
        .options(
            selectinload(User.airlines)
            .selectinload(Airline.asset)
        )
        .where(User.user_id == user_id)
    )

    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise ValueError("User not found")

    airlines_list = []

    for airline in user.airlines:
        airlines_list.append(
            AirlineSchema(
                airline_id=airline.id,
                airline_name=airline.airline_name,
                airline_icao=airline.icao,
                asset=map_asset(airline.asset)
            )
        )

    return AirlinesSchemaByUser(
        user=UserSchemaShort(
            user_id=user.user_id,
            user_mail=user.mail,
            user_displayname=user.display_name
        ),
        airlines=airlines_list
    ).model_dump(mode="json")


async def get_by_airline(session: AsyncSession, airline_id: Optional[int] = None,
                         airline_name: Optional[str] = None) -> AirlinesSchemaUsers:
    stmt = (
        select(Airline)
        .options(
            selectinload(Airline.asset),
            selectinload(Airline.users)
        )
    )

    if airline_id:
        stmt = stmt.where(Airline.id == airline_id)

    if airline_name:
        stmt = stmt.where(Airline.airline_name == airline_name)

    result = await session.execute(stmt)
    airline = result.scalar_one_or_none()

    if not airline:
        raise ValueError("Airline not found")

    users_list = []
    for user in airline.users:
        users_list.append(UserSchemaShort(
            user_id=user.user_id,
            user_mail=user.mail,
            user_displayname=user.display_name
        ))

    return AirlinesSchemaUsers(
        airline_id=airline.id,
        airline_name=airline.airline_name,
        airline_icao=airline.icao,
        asset=map_asset(asset=airline.asset),
        users=users_list
    ).model_dump(mode="json")


async def get_all_airlines(session: AsyncSession) -> list[AirlinesSchemaUsers]:
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

    response = []

    for airline in airlines:
        users_list = [
            UserSchemaShort(
                user_id=user.user_id,
                user_mail=user.mail,
                user_displayname=user.display_name
            )
            for user in airline.users
        ]

        response.append(
            AirlinesSchemaUsers(
                airline_id=airline.id,
                airline_name=airline.airline_name,
                airline_icao=airline.icao,
                asset=map_asset(asset=airline.asset),
                users=users_list
            ).model_dump(mode="json")
        )

    return response


async def query_airline(session: AsyncSession, airline_name: Optional[str], airline_id: Optional[int],
                        user_id: Optional[UUID]) -> AirlinesSchemaUsers | AirlinesSchemaByUser | list[
    AirlinesSchemaUsers]:
    try:
        if user_id:
            return await get_by_user_id(session, user_id)

        if airline_id or airline_name:
            return await get_by_airline(session, airline_id, airline_name)

        return await get_all_airlines(session)
    except Exception as _ex:
        raise _ex


async def query_templates(session: AsyncSession, template_name: Optional[str], template_id: Optional[int]) -> list[
    AircraftTemplateSchema]:
    stmt = (
        select(AircraftTemplate)
        .options(
            selectinload(AircraftTemplate.asset),
        )
        .order_by(AircraftTemplate.template_name)
    )

    if template_name:
        stmt = stmt.where(AircraftTemplate.template_name == template_name)
    if template_id:
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

            asset = ApplicationAsset(
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
                          template_id: Optional[int], template_name: Optional[str], aircraft_registration: Optional[str],
                          aircraft_msn: Optional[int], aircraft_id: Optional[int]) -> list[AircraftSchema]:
    stmt = (
        select(Aircraft)
        .join(Aircraft.airline)
        .join(Aircraft.template)
        .options(
            selectinload(Aircraft.airline)
            .selectinload(Airline.asset),
            selectinload(Aircraft.template)
            .selectinload(AircraftTemplate.asset),
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
    aircrafts =  result.scalars().all()

    aircrafts_list = []

    for aircraft in aircrafts:
        aircrafts_list.append(AircraftSchema(
            registration=aircraft.registration,
            msn=aircraft.msn,
            policy_from=aircraft.policy_from,
            policy_to=aircraft.policy_to,
            hulldeductible_franchise=aircraft.hulldeductible_franchise,
            threshold=aircraft.threshold,
            in_dashboard=aircraft.in_dashboard,
            status=aircraft.status,
            airline=AirlineSchema(
                airline_id=aircraft.airline.id,
                airline_name=aircraft.airline.airline_name,
                airline_icao=aircraft.airline.icao,
                asset=map_asset(asset=aircraft.airline.asset)
            ),
            template=AircraftTemplateSchema(
                template_id=aircraft.template.id,
                template_name=aircraft.template.template_name,
                asset=map_asset(asset=aircraft.template.asset)
            )
        ))

    return aircrafts_list


async def query_create_aircraft(session: AsyncSession, *, aircraft_registration: str, aircraft_msn: int, airline_id: int, template_id: int,
                          policy_from: date | None = None, policy_to: date | None = None,
                          hulldeductible_franchise: float | None = None, threshold: float | None = None,
                          in_dashboard: bool = False, status: str = "Insured") -> bool:

    airline = await session.get(Airline, airline_id)
    if not airline:
        raise ValueError("Airline not found")

    template = await session.get(AircraftTemplate, template_id)
    if not template:
        raise ValueError("Aircraft template not found")

    aircraft = Aircraft(
        registration=aircraft_registration,
        msn=aircraft_msn,
        airline_id=airline_id,
        template_id=template_id,
        policy_from=policy_from,
        policy_to=policy_to,
        hulldeductible_franchise=hulldeductible_franchise,
        threshold=threshold,
        in_dashboard=in_dashboard,
        status=status,
    )

    session.add(aircraft)

    return True

