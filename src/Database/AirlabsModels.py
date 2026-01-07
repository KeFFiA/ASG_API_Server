from datetime import datetime

from sqlalchemy import String, BigInteger, Float, Integer, SmallInteger, Enum, DateTime, Index, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .config import AirlabsBase as Base

try:
    from Schemas.Enums.Defaults import FlightStatusEnum
except ImportError:
    from ..Schemas.Enums.Defaults import FlightStatusEnum

class FlightSnapshot(Base):
    # identifiers
    hex: Mapped[str] = mapped_column(String(6), nullable=False)
    reg_number: Mapped[str] = mapped_column(String(16), nullable=False)

    airline_icao: Mapped[str] = mapped_column(String(3))
    airline_iata: Mapped[str] = mapped_column(String(2))

    aircraft_icao: Mapped[str] = mapped_column(String(4))

    flight_icao: Mapped[str] = mapped_column(String(10))
    flight_iata: Mapped[str] = mapped_column(String(10))
    flight_number: Mapped[str] = mapped_column(String(10))

    # airports
    dep_icao: Mapped[str] = mapped_column(String(4))
    dep_iata: Mapped[str] = mapped_column(String(3))
    arr_icao: Mapped[str] = mapped_column(String(4))
    arr_iata: Mapped[str] = mapped_column(String(3))

    # geo / motion
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    alt: Mapped[int] = mapped_column(Integer)  # meters
    dir: Mapped[int] = mapped_column(SmallInteger)  # degrees 0–360
    speed: Mapped[int] = mapped_column(Integer)  # km/h
    v_speed: Mapped[int] = mapped_column(Integer)  # km/h

    squawk: Mapped[str] = mapped_column(String(4))
    flag: Mapped[str] = mapped_column(String(2))

    status: Mapped[FlightStatusEnum] = mapped_column(
        Enum(
            FlightStatusEnum,
            name="flight_status",
            native_enum=True,
            create_constraint=False
        ),
        nullable=False
    )

    updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )

    current_state = relationship(
        "AircraftState",
        back_populates="snapshot",
        uselist=False,
        primaryjoin="FlightSnapshot.reg_number==foreign(AircraftState.reg_number)"
    )


class AircraftState(Base):
    reg_number: Mapped[str] = mapped_column(String(16), primary_key=True)

    airline_icao: Mapped[str] = mapped_column(String(3), index=True)
    airline_iata: Mapped[str] = mapped_column(String(2), index=True)

    status: Mapped[FlightStatusEnum] = mapped_column(
        Enum(
            FlightStatusEnum,
            name="flight_status",
            native_enum=True,
            create_constraint=False
        ),
        nullable=False
    )

    last_update: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    snapshot_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("flightsnapshots.id", ondelete="SET NULL"),
        nullable=True
    )

    snapshot: Mapped["FlightSnapshot"] = relationship(
        "FlightSnapshot",
        back_populates="current_state",
        lazy="joined"
    )


Index("ix_snapshots_reg_number", FlightSnapshot.reg_number)
Index("ix_snapshots_airline_icao", FlightSnapshot.airline_icao)
Index("ix_snapshots_airline_iata", FlightSnapshot.airline_iata)
Index("ix_snapshots_updated", FlightSnapshot.updated)

Index(
    "ix_snapshots_reg_updated",
    FlightSnapshot.reg_number,
    FlightSnapshot.updated.desc()
)

Index(
    "ix_snapshots_reg_status",
    FlightSnapshot.reg_number,
    FlightSnapshot.status,
)
