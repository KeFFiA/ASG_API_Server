from datetime import date, datetime
from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from Database import Claim, Aircraft, User, Airline, AircraftTemplate
from Schemas import GetClaimSchema, AircraftSchema, AirlineSchema, UserSchemaShort, CreateClaimBodySchema, \
    SumPolicyBodySchema, SumPolicyResponseSchema, ClaimsDeleteQuery
from Schemas.Enums import UpsertStatusEnum
from Utils import map_asset


async def query_claims(session: AsyncSession, claim_id: Optional[int], user_id: Optional[UUID]) -> List[GetClaimSchema]:
    try:
        stmt = (
            select(Claim)
            .options(
                selectinload(Claim.aircraft)
                .selectinload(Aircraft.airline)
                .selectinload(Airline.asset),
                selectinload(Claim.aircraft)
                .selectinload(Aircraft.template)
                .selectinload(AircraftTemplate.asset),
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
                        user_displayname=user.display_name,
                        user_mail=user.mail,
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
                    currency=claim.currency,
                    currency_rate=claim.currency_rate,
                    hd_reserve=claim.hd_reserve,
                    hw_reserve=claim.hw_reserve,
                    hsl_reserve=claim.hsl_reserve,
                    hd_paid=claim.hd_paid,
                    hw_paid=claim.hw_paid,
                    hsl_paid=claim.hsl_paid
                ).model_dump(mode="json")
            )
        return claims_list

    except Exception as _ex:
        raise _ex


async def query_create_claim(session: AsyncSession, _payload: CreateClaimBodySchema):
    payload = CreateClaimBodySchema(**_payload.model_dump())

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

        if payload.date_of_loss:
            if not isinstance(payload.date_of_loss, date):
                payload.date_of_loss = datetime.fromisoformat(str(payload.date_of_loss)).date()

        if payload.paid_date:
            if not isinstance(payload.paid_date, date):
                payload.paid_date = datetime.fromisoformat(str(payload.paid_date)).date()

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


async def delete_claim_query(session: AsyncSession, _payload: ClaimsDeleteQuery):
    payload = ClaimsDeleteQuery(**_payload.model_dump())

    try:
        stmt = delete(Claim).where(Claim.id == payload.claim_id)
        await session.execute(stmt)
        await session.commit()
        return True
    except Exception as _ex:
        raise _ex


async def query_sum_policy(session: AsyncSession, _payload: SumPolicyBodySchema):
    payload = SumPolicyBodySchema(**_payload.model_dump())

    try:
        stmt = (
            select(Aircraft.threshold, Aircraft.hulldeductible_franchise)
            .where(Aircraft.id == _payload.aircraft_id)
        )
        result = await session.execute(stmt)
        threshold, franchise = result.one_or_none()

        # Флаги
        is_hd, is_hw, is_hsl = payload.is_hd, payload.is_hw, payload.is_hsl

        # Безопасные значения
        def safe_mul(a, b):
            return a * b if a is not None and b is not None else a

        reserve_total = safe_mul(payload.indemnity_reserve, payload.currency_rate)
        paid_total = safe_mul(payload.paid_to_date_amount, payload.currency_rate)

        # Безопасное деление
        def half(value):
            return round(value / 2, 2) if value is not None else None

        # HD Reserve
        if is_hd and not is_hw and not is_hsl and reserve_total is not None and franchise is not None:
            if reserve_total >= franchise:
                hd_reserve = (threshold - franchise) if threshold is not None and reserve_total > threshold else reserve_total - franchise
            else:
                hd_reserve = None
        else:
            hd_reserve = None

        # HW Reserve
        if is_hd and is_hw:
            hw_reserve = reserve_total if not is_hsl else half(reserve_total)
        else:
            hw_reserve = None

        # HSL Reserve
        if not is_hd and not is_hw and not is_hsl:
            hsl_reserve = reserve_total
        elif is_hd and is_hw and is_hsl:
            hsl_reserve = half(reserve_total)
        elif is_hd and not is_hw and not is_hsl and reserve_total is not None and hd_reserve is not None and franchise is not None and reserve_total > (hd_reserve + franchise):
            hsl_reserve = reserve_total - threshold if threshold is not None else None
        else:
            hsl_reserve = None

        # HD Paid
        hd_paid = paid_total if is_hd and not is_hw and not is_hsl else None

        # HW Paid
        if is_hd and is_hw:
            hw_paid = paid_total if not is_hsl else half(paid_total)
        else:
            hw_paid = None

        # HSL Paid
        if (not is_hd and not is_hw and not is_hsl) or (is_hd and not is_hw and not is_hsl and paid_total is not None and threshold is not None and paid_total > threshold):
            hsl_paid = paid_total
        elif is_hd and is_hw and is_hsl:
            hsl_paid = half(paid_total)
        else:
            hsl_paid = None

        return SumPolicyResponseSchema(
            hd_reserve=hd_reserve,
            hw_reserve=hw_reserve,
            hsl_reserve=hsl_reserve,
            hd_paid=hd_paid,
            hw_paid=hw_paid,
            hsl_paid=hsl_paid
        ).model_dump(mode="json")

    except Exception as _ex:
        raise _ex
