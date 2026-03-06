from typing import Optional, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from Database import Claim, Aircraft, User
from Schemas import GetClaimSchema, AircraftSchema, AirlineSchema, AircraftTemplateSchema, \
    UserSchemaShort, CreateClaimSchema
from Schemas.Enums import UpsertStatusEnum
from Utils import map_asset


async def query_claims(session, claim_id: Optional[int], user_id: Optional[UUID]) -> List[GetClaimSchema]:
    try:
        stmt = (
            select(Claim)
            .options(
                selectinload(Claim.aircraft)
                .selectinload(Aircraft.airline),

                selectinload(Claim.aircraft)
                .selectinload(Aircraft.template),

                selectinload(Claim.users)
            )
        )
        if claim_id:
            stmt = stmt.where(Claim.id == claim_id)
        if user_id:
            stmt = stmt.where(
                Claim.users.any(User.user_id == user_id)
            )

        result = await session.execute(stmt)
        claims = result.scalars().all()

        if not claims:
            raise ValueError("Claim not found")

        claims_list = []
        for claim in claims:
            users_list = []
            for user in claim.users:
                users_list.append(
                    UserSchemaShort(
                        user_id=user.user_id,
                        user_displayname=user.user_displayname,
                        user_mail=user.user_mail,
                    )
                )
            claims_list.append(
                GetClaimSchema(
                    claim_id=claim.id,
                    users=users_list,
                    aircraft=AircraftSchema(
                        aircraft_id=claim.aircraft.id,
                        registration=claim.aircraft.registration,
                        msn=claim.aircraft.msn,
                        policy_from=claim.aircraft.policy_from,
                        policy_to=claim.aircraft.policy_to,
                        hulldeductible_franchise=claim.aircraft.hulldeductible_franchise,
                        threshold=claim.aircraft.threshold,
                        in_dashboard=claim.aircraft.in_dashboard,
                        status=claim.aircraft.status,
                        airline=AirlineSchema(
                            airline_id=claim.aircraft.airline.id,
                            airline_name=claim.aircraft.airline.airline_name,
                            airline_icao=claim.aircraft.airline.icao,
                            asset=map_asset(claim.aircraft.airline.asset),
                        ),
                        template=AircraftTemplateSchema(
                            template_id=claim.aircraft.template.id,
                            template_name=claim.aircraft.template.template_name,
                            asset=map_asset(claim.aircraft.template.asset),
                        )
                    ),
                    date_of_loss=claim.date_of_loss,
                    location_of_loss=claim.location_of_loss,
                    status=claim.status,
                    damage=claim.damage,
                    indemnity_reserve_amount=claim.indemnity_reserve_amount,
                    paid_to_date_amount=claim.paid_to_date_amount,
                    paid_date=claim.paid_date,
                    is_hd=claim.is_hd,
                    is_hw=claim.is_hw,
                    is_hsl=claim.is_hsl,
                    leader=claim.leader,
                    surveyor=claim.surveyor,
                ).model_dump(mode="json")
            )
        return claims_list

    except Exception as _ex:
        raise _ex


async def query_create_claim(session, _payload: CreateClaimSchema):
    payload = CreateClaimSchema(**_payload.model_dump())

    try:
        claim = None

        if payload.claim_id:
            result = await session.execute(
                select(Claim)
                .options(selectinload(Claim.users))
                .where(Claim.id == payload.claim_id)
            )
            claim = result.scalar_one_or_none()

        user = None
        if payload.user_id:
            result = await session.execute(
                select(User).where(User.user_id == payload.user_id)
            )
            user = result.scalar_one()

        if claim:
            for field, value in payload.model_dump(exclude_unset=True).items():
                if field not in {"claim_id", "user_id"}:
                    setattr(claim, field, value)
            if user and user not in claim.users:
                claim.users.append(user)
            response = UpsertStatusEnum.UPDATED.value

        else:
            claim_data = payload.model_dump(exclude={"claim_id", "user_id"})
            claim = Claim(**claim_data)
            if user:
                claim.users.append(user)
            session.add(claim)
            response = UpsertStatusEnum.CREATED.value

        await session.commit()
        return response

    except Exception as _ex:
        raise _ex
