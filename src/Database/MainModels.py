import inspect
import sys
from datetime import datetime, date

from sqlalchemy import String, Integer, Float, Boolean, DateTime, Date
from sqlalchemy.orm import Mapped, mapped_column
from .config import MainBase as Base

try:
    from Schemas.Enums import MSGraphAPI
except ModuleNotFoundError:
    from ..Schemas.Enums import MSGraphAPI



class Registrations(Base):
    reg: Mapped[str] = mapped_column(String, unique=True)
    msn: Mapped[int] = mapped_column(Integer, nullable=True)
    aircraft_type: Mapped[str] = mapped_column(String, nullable=True)
    indashboard: Mapped[bool] = mapped_column(Boolean, default=False)


class Aircrafts(Base):
    aircraft_type: Mapped[str] = mapped_column(String, nullable=False)
    base64: Mapped[str] = mapped_column(String, nullable=True)


class Airlines(Base):
    name: Mapped[str] = mapped_column(String, unique=True)
    icao: Mapped[str] = mapped_column(String, nullable=True)
    base64: Mapped[str] = mapped_column(String, nullable=True)


class Guests(Base):
    guest_email: Mapped[str] = mapped_column(String, unique=True)
    guest_upn: Mapped[str] = mapped_column(String)
    guest_name: Mapped[str] = mapped_column(String, default=None)
    is_guest: Mapped[bool] = mapped_column(Boolean, default=False)
    inviter_email: Mapped[str] = mapped_column(String)
    expires_at: Mapped[date] = mapped_column(Date)
    invite_status: Mapped[int] = mapped_column(Integer, default=MSGraphAPI.InvitationStatusEnum.PENDING_ACCEPTANCE.code)

_current_module = sys.modules[__name__]

__all__ = [
    name
    for name, obj in globals().items()
    if inspect.isclass(obj) and obj.__module__ == __name__
]
