from typing import Optional, List
from uuid import UUID as UUID_Python

from sqlalchemy import String, Boolean, ForeignKey, UniqueConstraint, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .AssociationModels import application_access_rules
from ..config import PowerPlatformBase as Base


class Application(Base):
    application_id: Mapped[UUID_Python] = mapped_column(UUID, unique=True, index=True)
    application_name: Mapped[str] = mapped_column(String, nullable=False)
    application_description: Mapped[str] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="Work in progress")

    application_accesses: Mapped[List["Access"]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan"
    )

    rules: Mapped[List["Rule"]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan"
    )

    asset: Mapped[Optional["Asset"]] = relationship(
        "Asset",
        back_populates="application",
        uselist=False,
        cascade="all, delete-orphan"
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

    rules: Mapped[List["Rule"]] = relationship(
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


