from datetime import datetime
from sqlalchemy import DateTime, String, Boolean, ForeignKey, Table, Column, BigInteger, Integer
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .config import PowerPlatformBase as Base


class UserAssignedLicenseLink(Base):
    user_id: Mapped[str] = mapped_column(
        ForeignKey('users.user_id'),
        primary_key=True
    )
    license_id: Mapped[str] = mapped_column(
        ForeignKey('userassignedlicenses.license_id'),
        primary_key=True
    )

    user = relationship("User", back_populates="assigned_licenses_links")
    license = relationship("UserAssignedLicense", back_populates="users_links")

class User(Base):
    user_id: Mapped[str] = mapped_column(String, primary_key=True, unique=True)
    display_name: Mapped[str] = mapped_column(String, nullable=True)
    given_name: Mapped[str] = mapped_column(String, nullable=True)
    surname: Mapped[str] = mapped_column(String, nullable=True)
    user_principal_name: Mapped[str] = mapped_column(String, nullable=True)
    account_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=True)
    mail: Mapped[str] = mapped_column(String, nullable=True)
    mobile_phone: Mapped[str] = mapped_column(String, nullable=True)
    city: Mapped[str] = mapped_column(String, nullable=True)
    country: Mapped[str] = mapped_column(String, nullable=True)
    department: Mapped[str] = mapped_column(String, nullable=True)
    job_title: Mapped[str] = mapped_column(String, nullable=True)
    employee_id: Mapped[str] = mapped_column(String, nullable=True)
    employee_hire_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_date_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # Relationships
    assigned_licenses_links = relationship(
        "UserAssignedLicenseLink",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    @property
    def assigned_licenses(self):
        return [link.license for link in self.assigned_licenses_links]

    assigned_plans = relationship("UserAssignedPlan", back_populates="user")
    drives = relationship("UserDrive", back_populates="user")
    messages = relationship("UserMessage", back_populates="user")
    calendars = relationship("UserCalendar", back_populates="user")
    photos = relationship("UserPhoto", back_populates="user")
    contacts = relationship("UserContact", back_populates="user")
    manager_id: Mapped[str] = mapped_column(ForeignKey('users.user_id'), nullable=True)
    manager = relationship("User", remote_side=[user_id], backref="direct_reports")

    application_accesses = relationship(
        "ApplicationAccess",
        back_populates="user",
        cascade="all, delete-orphan"
    )


class UserAssignedLicense(Base):
    license_id: Mapped[str] = mapped_column(String, primary_key=True, unique=True)
    sku_id: Mapped[str] = mapped_column(String)
    disabled_plans: Mapped[str] = mapped_column(String, nullable=True)

    users_links = relationship(
        "UserAssignedLicenseLink",
        back_populates="license",
        cascade="all, delete-orphan"
    )


class UserAssignedPlan(Base):
    plan_id: Mapped[str] = mapped_column(String, primary_key=True, unique=True)
    capability_status: Mapped[str] = mapped_column(String, nullable=True)
    service: Mapped[str] = mapped_column(String, nullable=True)

    user_id: Mapped[str] = mapped_column(ForeignKey('users.user_id'))
    user = relationship("User", back_populates="assigned_plans")


class UserDrive(Base):
    drive_id: Mapped[str] = mapped_column(String, primary_key=True, unique=True)
    drive_type: Mapped[str] = mapped_column(String, nullable=True)

    user_id: Mapped[str] = mapped_column(ForeignKey('users.user_id'))
    user = relationship("User", back_populates="drives")


class UserMessage(Base):
    message_id: Mapped[str] = mapped_column(String, primary_key=True, unique=True)
    subject: Mapped[str] = mapped_column(String, nullable=True)
    body_preview: Mapped[str] = mapped_column(String, nullable=True)

    user_id: Mapped[str] = mapped_column(ForeignKey('users.user_id'))
    user = relationship("User", back_populates="messages")


class UserCalendar(Base):
    calendar_id: Mapped[str] = mapped_column(String, primary_key=True, unique=True)
    name: Mapped[str] = mapped_column(String, nullable=True)

    user_id: Mapped[str] = mapped_column(ForeignKey('users.user_id'))
    user = relationship("User", back_populates="calendars")


class UserPhoto(Base):
    photo_id: Mapped[str] = mapped_column(String, primary_key=True, unique=True)
    url: Mapped[str] = mapped_column(String, nullable=True)

    user_id: Mapped[str] = mapped_column(ForeignKey('users.user_id'))
    user = relationship("User", back_populates="photos")


class UserContact(Base):
    contact_id: Mapped[str] = mapped_column(String, primary_key=True, unique=True)
    display_name: Mapped[str] = mapped_column(String, nullable=True)
    email: Mapped[str] = mapped_column(String, nullable=True)

    user_id: Mapped[str] = mapped_column(ForeignKey('users.user_id'))
    user = relationship("User", back_populates="contacts")


class Application(Base):
    application_id: Mapped[str] = mapped_column(String, primary_key=True, unique=True)
    application_name: Mapped[str] = mapped_column(String, nullable=True)
    application_description: Mapped[str] = mapped_column(String, nullable=True)

    application_accesses = relationship(
        "ApplicationAccess",
        back_populates="application",
        cascade="all, delete-orphan"
    )


class ApplicationAccess(Base):
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.user_id"),
        primary_key=True
    )
    application_id: Mapped[str] = mapped_column(
        ForeignKey("applications.application_id"),
        primary_key=True
    )
    rules: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False, default=list)
    main_access: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    super_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user = relationship("User", back_populates="application_accesses")
    application = relationship("Application", back_populates="application_accesses")
