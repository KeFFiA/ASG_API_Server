from datetime import datetime, date
from typing import Optional, List
from uuid import UUID as UUID_Python

from sqlalchemy import DateTime, String, Boolean, ForeignKey, ForeignKeyConstraint, UniqueConstraint, Table, Column, \
    Integer, LargeBinary, Date, Float
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .config import PowerPlatformBase as Base


_claim_users = Table(
    "_claim_users",
    Base.metadata,
    Column("claim_id", ForeignKey("claims.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    user_id: Mapped[UUID_Python] = mapped_column(UUID, unique=True, index=True)

    display_name: Mapped[str] = mapped_column(String, nullable=True)
    given_name: Mapped[str] = mapped_column(String, nullable=True)
    surname: Mapped[str] = mapped_column(String, nullable=True)
    user_principal_name: Mapped[str] = mapped_column(String, nullable=True)
    account_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=True)
    mail: Mapped[str] = mapped_column(String, nullable=True)
    mobile_phone: Mapped[str] = mapped_column(String, nullable=True)
    business_phones: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=True)
    city: Mapped[str] = mapped_column(String, nullable=True)
    country: Mapped[str] = mapped_column(String, nullable=True)
    department: Mapped[str] = mapped_column(String, nullable=True)
    job_title: Mapped[str] = mapped_column(String, nullable=True)
    employee_id: Mapped[str] = mapped_column(String, nullable=True)
    employee_hire_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_date_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    super_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


    manager_id: Mapped[UUID_Python | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    manager: Mapped["User"] = relationship(
        remote_side="User.id",
        back_populates="direct_reports"
    )

    direct_reports: Mapped[list["User"]] = relationship(back_populates="manager")

    application_accesses: Mapped[list["Access"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )

    airlines: Mapped[list["Airline"]] = relationship(
        secondary="userairlineaccesses",
        back_populates="users"
    )

    claims: Mapped[List["Claim"]] = relationship(
        secondary=_claim_users,
        back_populates="users"
    )


class Application(Base):
    application_id: Mapped[UUID_Python] = mapped_column(UUID, unique=True, index=True)
    application_name: Mapped[str] = mapped_column(String, nullable=False)
    application_description: Mapped[str] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="Work in progress")

    application_accesses: Mapped[list["Access"]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan"
    )

    rules: Mapped[list["Rule"]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan"
    )

    asset: Mapped[Optional["Asset"]] = relationship(
        "Asset",
        back_populates="application",
        uselist=False,
        cascade="all, delete-orphan"
    )


application_access_rules = Table(
    "application_access_rules",
    Base.metadata,

    Column("user_id", UUID, primary_key=True),
    Column("application_id", UUID, primary_key=True),
    Column(
        "rule_id",
        ForeignKey("rules.id", ondelete="CASCADE"),
        primary_key=True
    ),

    ForeignKeyConstraint(
        ["user_id", "application_id"],
        ["accesses.user_id", "accesses.application_id"],
        ondelete="CASCADE"
    ),
)


class Access(Base):
    __table_args__ = (
        UniqueConstraint("user_id", "application_id", name="user_application_uq"),
    )

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)
    application_id: Mapped[UUID_Python] = mapped_column(ForeignKey("applications.application_id", ondelete="CASCADE"),
                                                        primary_key=True)

    main_access: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user: Mapped["User"] = relationship(back_populates="application_accesses")
    application: Mapped["Application"] = relationship(back_populates="application_accesses")

    rules: Mapped[list["Rule"]] = relationship(
        secondary=application_access_rules,
        lazy="selectin"
    )


class Rule(Base):
    application_id: Mapped[UUID] = mapped_column(
        ForeignKey("applications.application_id", ondelete="CASCADE"),
        index=True
    )

    rule_name: Mapped[str] = mapped_column(String, nullable=False)
    rule_description: Mapped[str] = mapped_column(String)

    application: Mapped["Application"] = relationship(
        back_populates="rules"
    )


class Font(Base):
    screen_size: Mapped[int] = mapped_column(Integer, nullable=False)
    usage_name: Mapped[str] = mapped_column(String, nullable=False)
    font_name: Mapped[str] = mapped_column(String, nullable=False)
    font_size: Mapped[int] = mapped_column(Integer, nullable=False)
    font_color: Mapped[str] = mapped_column(String, nullable=False)
    font_weight: Mapped[str] = mapped_column(String, nullable=False)


class Asset(Base):
    asset_name: Mapped[str] = mapped_column(String, nullable=False)
    asset_description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    mime_type: Mapped[str] = mapped_column(String, nullable=False)
    base64: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    airline: Mapped["Airline"] = relationship(back_populates="asset")
    aircraft_template: Mapped["AircraftTemplate"] = relationship(
        back_populates="asset",
        uselist=False
    )

    application_id: Mapped[UUID_Python] = mapped_column(
        UUID, ForeignKey("applications.application_id"), nullable=True
    )

    application: Mapped["Application"] = relationship(
        "Application",
        back_populates="asset",
        uselist=False
    )




class UserAirlineAccess(Base):
    user_id: Mapped[UUID_Python] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True
    )

    airline_id: Mapped[int] = mapped_column(
        ForeignKey("airlines.id", ondelete="CASCADE"),
        primary_key=True
    )


class Airline(Base):
    airline_name: Mapped[str] = mapped_column(String, nullable=False)
    icao: Mapped[str] = mapped_column(String, nullable=False)

    asset_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
        unique=True  # 1-2-1
    )

    asset: Mapped[Optional["Asset"]] = relationship(
        back_populates="airline",
        uselist=False
    )

    users: Mapped[list["User"]] = relationship(
        secondary="userairlineaccesses",
        back_populates="airlines"
    )

    aircrafts: Mapped[list["Aircraft"]] = relationship(
        back_populates="airline",
        cascade="all, delete-orphan"
    )


class AircraftTemplate(Base):
    template_name: Mapped[str] = mapped_column(String, nullable=False)

    asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
        unique=True
    )

    asset: Mapped["Asset"] = relationship(
        back_populates="aircraft_template",
        uselist=False
    )

    aircrafts: Mapped[list["Aircraft"]] = relationship(
        back_populates="template"
    )


class AircraftPolicy(Base):
    aircraft_id: Mapped[int] = mapped_column(ForeignKey("aircraft.id", ondelete="CASCADE"), nullable=False)

    policy_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    policy_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    aircraft: Mapped["Aircraft"] = relationship(back_populates="policy")

    claims: Mapped[list["Claim"]] = relationship(back_populates="policy", cascade="all, delete-orphan")


class Aircraft(Base):
    registration: Mapped[str] = mapped_column(String, nullable=False)
    msn: Mapped[int] = mapped_column(Integer, nullable=False)

    airline_id: Mapped[int] = mapped_column(
        ForeignKey("airlines.id", ondelete="CASCADE"),
        nullable=False
    )

    template_id: Mapped[int] = mapped_column(
        ForeignKey("aircrafttemplates.id", ondelete="RESTRICT"),
        nullable=False
    )

    policy: Mapped[list["AircraftPolicy"]] = relationship(back_populates="aircraft", cascade="all, delete-orphan")

    engines_manufacture: Mapped[str] = mapped_column(String, nullable=True)
    engines_model: Mapped[str] = mapped_column(String, nullable=True)
    number_of_engines: Mapped[int] = mapped_column(Integer, nullable=True, default=2)
    engine1_msn: Mapped[int] = mapped_column(Integer, nullable=True)
    engine2_msn: Mapped[int] = mapped_column(Integer, nullable=True)
    engine3_msn: Mapped[int] = mapped_column(Integer, nullable=True)
    engine4_msn: Mapped[int] = mapped_column(Integer, nullable=True)

    agreed_value: Mapped[float] = mapped_column(Float, nullable=True, default=0.0)
    agreed_value_down_absolute: Mapped[float] = mapped_column(Float, nullable=True, default=0.0)
    agreed_value_down_percent: Mapped[float] = mapped_column(Float, nullable=True, default=0.0)
    combined_single_limit: Mapped[float] = mapped_column(Float, nullable=True, default=0.0)
    all_risks_deductible: Mapped[float] = mapped_column(Float, nullable=True, default=0.0)
    hull_and_spares_excess: Mapped[float] = mapped_column(Float, nullable=True, default=0.0)

    lessee: Mapped[str] = mapped_column(String, nullable=True)
    lessor: Mapped[str] = mapped_column(String, nullable=True)

    in_dashboard: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="Insured")

    airline: Mapped["Airline"] = relationship(back_populates="aircrafts")
    template: Mapped["AircraftTemplate"] = relationship(back_populates="aircrafts")

    claims: Mapped[list["Claim"]] = relationship(back_populates="aircraft")


class Claim(Base):
    aircraft_id: Mapped[int] = mapped_column(
        ForeignKey("aircraft.id", ondelete="RESTRICT"),
        nullable=False
    )

    aircraft: Mapped["Aircraft"] = relationship(back_populates="claims")

    users: Mapped[List["User"]] = relationship(
        secondary=_claim_users,
        back_populates="claims"
    )

    policy: Mapped["AircraftPolicy"] = relationship(
        back_populates="claims"
    )

    date_of_loss: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    location_of_loss: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    status: Mapped[str] = mapped_column(String, nullable=False, default="Opened")

    damage: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    indemnity_reserve_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    paid_to_date_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    paid_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    is_hd: Mapped[bool] = mapped_column(Boolean, default=False)
    is_hw: Mapped[bool] = mapped_column(Boolean, default=False)
    is_hsl: Mapped[bool] = mapped_column(Boolean, default=False)

    leader: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    surveyor: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    currency: Mapped[Optional[str]] = mapped_column(String, nullable=True, default="USD")
    currency_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=1)

    hd_reserve: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    hw_reserve: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    hsl_reserve: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    hd_paid: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    hw_paid: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    hsl_paid: Mapped[Optional[float]] = mapped_column(Float, nullable=True)





