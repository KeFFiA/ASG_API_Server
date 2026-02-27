from datetime import datetime
from sqlalchemy import DateTime, String, Boolean, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .config import PowerPlatformBase as Base


class User(Base):
    user_id: Mapped[str] = mapped_column(String, unique=True, index=True)

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

    manager_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    manager: Mapped["User"] = relationship(
        remote_side="User.id",
        back_populates="direct_reports"
    )

    direct_reports: Mapped[list["User"]] = relationship(
        back_populates="manager"
    )

    photos: Mapped[list["UserPhoto"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )

    application_accesses: Mapped[list["ApplicationAccess"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )


class UserPhoto(Base):
    photo_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    url: Mapped[str] = mapped_column(String, nullable=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user: Mapped["User"] = relationship(back_populates="photos")


class Application(Base):
    application_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    application_name: Mapped[str] = mapped_column(String, nullable=True)
    application_description: Mapped[str] = mapped_column(String, nullable=True)

    application_accesses: Mapped[list["ApplicationAccess"]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan"
    )


class ApplicationAccess(Base):
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    rules: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False, default=list)
    main_access: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    super_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    user: Mapped["User"] = relationship(back_populates="application_accesses")
    application: Mapped["Application"] = relationship(back_populates="application_accesses")