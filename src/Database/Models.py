from sqlalchemy import String, Integer, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from .config import Base


class PDF_Queue(Base):
    filename: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    queue_position: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="Queued")
    status_description: Mapped[str] = mapped_column(String, nullable=False, default="Pending")
    user_email: Mapped[str] = mapped_column(String, nullable=False)
    progress: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    progress_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    progress_done: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Registrations(Base):
    reg: Mapped[str] = mapped_column(String, unique=True)
    msn: Mapped[int] = mapped_column(Integer, nullable=True)
    aircraft_type: Mapped[str] = mapped_column(String, nullable=True)
    indashboard: Mapped[bool] = mapped_column(Boolean, default=False)
