from datetime import datetime

from sqlalchemy import DateTime, String, Integer, Float, Boolean

from .config import FlightRadarBase as Base
from sqlalchemy.orm import Mapped, mapped_column


class FlightSummary(Base):
    fr24_id: Mapped[str] = mapped_column(String, nullable=True)
    flight: Mapped[str] = mapped_column(String, nullable=True)

    callsign: Mapped[str] = mapped_column(String, nullable=True)
    operating_as: Mapped[str] = mapped_column(String, nullable=True, index=True)
    painted_as: Mapped[str] = mapped_column(String, nullable=True, index=True)

    type: Mapped[str] = mapped_column(String, nullable=True, index=True)
    reg: Mapped[str] = mapped_column(String, nullable=True, index=True)

    orig_icao: Mapped[str] = mapped_column(String, nullable=True, index=True)
    orig_iata: Mapped[str] = mapped_column(String, nullable=True, index=True)

    datetime_takeoff: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    runway_takeoff: Mapped[str] = mapped_column(String, nullable=True)

    dest_icao: Mapped[str] = mapped_column(String, nullable=True, index=True)
    dest_iata: Mapped[str] = mapped_column(String, nullable=True, index=True)
    dest_icao_actual: Mapped[str] = mapped_column(String, nullable=True, index=True)
    dest_iata_actual: Mapped[str] = mapped_column(String, nullable=True, index=True)

    datetime_landed: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    runway_landed: Mapped[str] = mapped_column(String, nullable=True)

    flight_time: Mapped[int] = mapped_column(Integer, nullable=True)
    actual_distance: Mapped[float] = mapped_column(Float, nullable=True)
    circle_distance: Mapped[float] = mapped_column(Float, nullable=True)

    category: Mapped[str] = mapped_column(String, nullable=True)
    hex: Mapped[str] = mapped_column(String, nullable=True)

    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    flight_ended: Mapped[bool] = mapped_column(Boolean, nullable=True)


class LivePositions(Base):
    fr24_id: Mapped[str] = mapped_column(String, nullable=True)
    flight: Mapped[str] = mapped_column(String, nullable=True)
    hex: Mapped[str] = mapped_column(String, nullable=True)

    callsign: Mapped[str] = mapped_column(String, nullable=True)

    lat: Mapped[float] = mapped_column(Float, nullable=True)
    lon: Mapped[float] = mapped_column(Float, nullable=True)
    alt: Mapped[float] = mapped_column(Float, nullable=True)
    gspeed: Mapped[float] = mapped_column(Float, nullable=True)
    vspeed: Mapped[float] = mapped_column(Float, nullable=True)

    track: Mapped[int] = mapped_column(Integer, nullable=True)

    squawk: Mapped[str] = mapped_column(String, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str] = mapped_column(String, nullable=True)

    orig_icao: Mapped[str] = mapped_column(String, nullable=True, index=True)
    orig_iata: Mapped[str] = mapped_column(String, nullable=True, index=True)
    dest_icao: Mapped[str] = mapped_column(String, nullable=True, index=True)
    dest_iata: Mapped[str] = mapped_column(String, nullable=True, index=True)

    type: Mapped[str] = mapped_column(String, nullable=True)
    reg: Mapped[str] = mapped_column(String, nullable=True, index=True)
    operating_as: Mapped[str] = mapped_column(String, nullable=True, index=True)
    painted_as: Mapped[str] = mapped_column(String, nullable=True, index=True)

    eta: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

