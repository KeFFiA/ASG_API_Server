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


class Guests(Base):
    guest_email: Mapped[str] = mapped_column(String, unique=True)
    guest_upn: Mapped[str] = mapped_column(String)
    guest_name: Mapped[str] = mapped_column(String, default=None)
    is_guest: Mapped[bool] = mapped_column(Boolean, default=False)
    inviter_email: Mapped[str] = mapped_column(String)
    expires_at: Mapped[date] = mapped_column(Date)
    invite_status: Mapped[int] = mapped_column(Integer, default=MSGraphAPI.InvitationStatusEnum.PENDING_ACCEPTANCE.code)


class Lease_Outputs(Base):
    aircraft_count: Mapped[int] = mapped_column(Integer, default=0)
    engines_count: Mapped[int] = mapped_column(Integer, default=0)
    aircraft_type: Mapped[str] = mapped_column(String, nullable=True)
    msn: Mapped[str] = mapped_column(String, nullable=True)
    engines_manufacturer: Mapped[str] = mapped_column(String, nullable=True)
    engines_models: Mapped[str] = mapped_column(String, nullable=True)
    engine1_msn: Mapped[str] = mapped_column(String, nullable=True)
    engine2_msn: Mapped[str] = mapped_column(String, nullable=True)
    aircraft_registration: Mapped[str] = mapped_column(String, nullable=True)
    dated: Mapped[str] = mapped_column(String, nullable=True)
    lesse: Mapped[str] = mapped_column(String, nullable=True)
    lessor: Mapped[str] = mapped_column(String, nullable=True)
    currency: Mapped[str] = mapped_column(String, nullable=True)
    damage_proceeds: Mapped[str] = mapped_column(String, nullable=True)
    Threshold: Mapped[str] = mapped_column(String, nullable=True)
    aircraft_agreed_value: Mapped[str] = mapped_column(String, nullable=True)
    aircraft_hull_all_risks: Mapped[str] = mapped_column(String, nullable=True)
    min_liability_coverages: Mapped[str] = mapped_column(String, nullable=True)
    all_risks_deductible: Mapped[str] = mapped_column(String, nullable=True)


_current_module = sys.modules[__name__]

__all__ = [
    name
    for name, obj in globals().items()
    if inspect.isclass(obj) and obj.__module__ == __name__
]
