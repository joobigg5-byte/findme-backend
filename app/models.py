"""
SQLAlchemy ORM models.

Schema mirrors the shape of the BUILDINGS object already used by the
find-me frontend (facility -> directory items + staff), with two things
the frontend never had: a real Organization (the paying customer) that
every Facility belongs to, and a real User with a hashed password.

Every query that touches Facility, DirectoryItem, StaffMember, or Caution
MUST be scoped by organization_id (directly or via facility.organization_id).
That scoping is what makes this multi-tenant — see routers/facilities.py
for how it's enforced, and test_backend.py for proof it's actually enforced.
"""
import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Float, ForeignKey, DateTime, UniqueConstraint
)
from sqlalchemy.orm import relationship
from .database import Base


def utcnow():
    return datetime.datetime.utcnow()


class Organization(Base):
    """The paying customer account — e.g. 'Grand Plaza Hotel' or a hotel chain."""
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    plan = Column(String(50), nullable=False, default="starter")  # starter | professional | enterprise
    created_at = Column(DateTime, default=utcnow)

    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    facilities = relationship("Facility", back_populates="organization", cascade="all, delete-orphan")


class User(Base):
    """An admin user belonging to exactly one Organization."""
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    reset_token = Column(String(255), nullable=True, index=True)
    reset_token_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    organization = relationship("Organization", back_populates="users")


class Facility(Base):
    """One physical building/location — the same shape as a BUILDINGS[id] entry."""
    __tablename__ = "facilities"
    __table_args__ = (UniqueConstraint("slug", name="uq_facilities_slug"),)

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)

    slug = Column(String(120), nullable=False, index=True)  # used in QR codes / deep links
    name = Column(String(200), nullable=False)
    subtitle = Column(String(200), default="")
    tagline = Column(Text, default="")
    receptionist = Column(String(100), default="")
    address = Column(String(300), default="")
    hours = Column(String(200), default="")
    city = Column(String(120), default="")
    country = Column(String(120), default="")
    category = Column(String(60), default="")
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    template_type = Column(String(30), nullable=True)  # 'mall' | 'restaurant' | null (general)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    organization = relationship("Organization", back_populates="facilities")
    directory_items = relationship("DirectoryItem", back_populates="facility", cascade="all, delete-orphan")
    staff = relationship("StaffMember", back_populates="facility", cascade="all, delete-orphan")
    cautions = relationship("Caution", back_populates="facility", cascade="all, delete-orphan")


class DirectoryItem(Base):
    """A room / person / place within a Facility — matches directory[] entries."""
    __tablename__ = "directory_items"

    id = Column(Integer, primary_key=True)
    facility_id = Column(Integer, ForeignKey("facilities.id"), nullable=False, index=True)

    name = Column(String(200), nullable=False)
    category = Column(String(20), nullable=False, default="places")  # people | rooms | places
    floor = Column(String(60), default="")
    room = Column(String(60), default="")
    description = Column(Text, default="")
    status = Column(String(20), nullable=True)  # available | busy | open | null
    icon = Column(String(40), default="door")

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    facility = relationship("Facility", back_populates="directory_items")


class StaffMember(Base):
    """A staff member within a Facility — matches getme.staff[] entries."""
    __tablename__ = "staff_members"

    id = Column(Integer, primary_key=True)
    facility_id = Column(Integer, ForeignKey("facilities.id"), nullable=False, index=True)
    dest_directory_item_id = Column(Integer, ForeignKey("directory_items.id"), nullable=True)

    name = Column(String(200), nullable=False)
    role = Column(String(150), default="")
    department = Column(String(150), default="")
    phone = Column(String(60), default="")
    email = Column(String(255), default="")
    hours = Column(String(200), default="")
    handles_json = Column(Text, default="[]")  # JSON-encoded list of strings
    today_status = Column(String(20), default="in")  # in | remote | out

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    facility = relationship("Facility", back_populates="staff")


class Caution(Base):
    """A live notice — matches getme.cautions[] entries. Staff post, guests see it instantly."""
    __tablename__ = "cautions"

    id = Column(Integer, primary_key=True)
    facility_id = Column(Integer, ForeignKey("facilities.id"), nullable=False, index=True)

    title = Column(String(300), nullable=False)
    area = Column(String(150), default="")
    description = Column(Text, default="")

    created_at = Column(DateTime, default=utcnow)

    facility = relationship("Facility", back_populates="cautions")
