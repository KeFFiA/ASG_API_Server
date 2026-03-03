from datetime import datetime
from uuid import UUID as UUID_Python

from sqlalchemy import DateTime, String, Boolean, ForeignKey, ForeignKeyConstraint, UniqueConstraint, Table, Column
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .config import PowerPlatformBase as Base


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

    application_accesses: Mapped[list["ApplicationAccess"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )


class Application(Base):
    application_id: Mapped[UUID_Python] = mapped_column(UUID, unique=True, index=True)
    application_name: Mapped[str] = mapped_column(String, nullable=True)
    application_description: Mapped[str] = mapped_column(String, nullable=True)

    application_accesses: Mapped[list["ApplicationAccess"]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan"
    )

    rules: Mapped[list["ApplicationRule"]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan"
    )


application_access_rules = Table(
    "application_access_rules",
    Base.metadata,

    Column("user_id", UUID, primary_key=True),
    Column("application_id", UUID, primary_key=True),
    Column(
        "rule_id",
        ForeignKey("applicationrules.id", ondelete="CASCADE"),
        primary_key=True
    ),

    ForeignKeyConstraint(
        ["user_id", "application_id"],
        ["applicationaccesses.user_id", "applicationaccesses.application_id"],
        ondelete="CASCADE"
    ),
)


class ApplicationAccess(Base):
    __table_args__ = (
        UniqueConstraint("user_id", "application_id", name="user_application_uq"),
    )

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)
    application_id: Mapped[UUID_Python] = mapped_column(ForeignKey("applications.application_id", ondelete="CASCADE"),
                                                        primary_key=True)

    main_access: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    super_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user: Mapped["User"] = relationship(back_populates="application_accesses")
    application: Mapped["Application"] = relationship(back_populates="application_accesses")

    rules: Mapped[list["ApplicationRule"]] = relationship(
        secondary=application_access_rules,
        lazy="selectin"
    )


class ApplicationRule(Base):
    application_id: Mapped[UUID] = mapped_column(
        ForeignKey("applications.application_id", ondelete="CASCADE"),
        index=True
    )

    rule_name: Mapped[str] = mapped_column(String, nullable=False)
    rule_description: Mapped[str] = mapped_column(String)

    application: Mapped["Application"] = relationship(
        back_populates="rules"
    )
