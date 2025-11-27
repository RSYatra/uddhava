"""
SQLAlchemy database models.

This module contains all the database table definitions using SQLAlchemy ORM.
Enhanced devotee management system for ISKCON Radha Shyam Sundar Yatra.
"""

from enum import Enum

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    event,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class UserRole(str, Enum):
    """User roles enumeration."""

    USER = "USER"
    ADMIN = "ADMIN"


class Gender(str, Enum):
    """Gender enumeration."""

    MALE = "M"
    FEMALE = "F"


class MaritalStatus(str, Enum):
    """Marital status enumeration."""

    BACHELOR = "BACHELOR"
    GRHASTA = "GRHASTA"
    VANPRASTHA = "VANPRASTHA"
    SANYAS = "SANYAS"
    DIVORCED = "DIVORCED"
    WIDOWED = "WIDOWED"


class InitiationStatus(str, Enum):
    """ISKCON initiation status enumeration."""

    ASPIRING = "ASPIRING"
    HARINAM = "HARINAM"
    BRAHMIN = "BRAHMIN"


class YatraStatus(str, Enum):
    """Yatra status enumeration."""

    DRAFT = "DRAFT"
    UPCOMING = "UPCOMING"
    REGISTRATION_CLOSED = "REGISTRATION_CLOSED"
    ONGOING = "ONGOING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class RegistrationStatus(str, Enum):
    """Yatra registration status enumeration."""

    DRAFT = "DRAFT"
    PENDING = "PENDING"
    PAYMENT_SUBMITTED = "PAYMENT_SUBMITTED"
    PAYMENT_VERIFIED = "PAYMENT_VERIFIED"
    CONFIRMED = "CONFIRMED"
    CANCELLED_BY_USER = "CANCELLED_BY_USER"
    CANCELLED_BY_ADMIN = "CANCELLED_BY_ADMIN"
    COMPLETED = "COMPLETED"


class RoomPreference(str, Enum):
    """Room preference enumeration."""

    SINGLE = "SINGLE"
    DOUBLE_SHARING = "DOUBLE_SHARING"
    TRIPLE_SHARING = "TRIPLE_SHARING"
    QUAD_SHARING = "QUAD_SHARING"
    DORMITORY = "DORMITORY"


class Devotee(Base):
    """
    Comprehensive devotee model for ISKCON Radha Shyam Sundar Yatra.

    This model captures all essential information about devotees including
    personal details, spiritual journey, and ISKCON-specific information.
    """

    __tablename__ = "devotees"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Authentication (consistent with existing system)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    # Email verification
    email_verified = Column(Boolean, nullable=False, default=False)
    verification_token = Column(String(255), nullable=True)
    verification_expires = Column(DateTime(timezone=True), nullable=True)

    # Personal Information
    legal_name = Column(String(127), nullable=False)
    date_of_birth = Column(Date, nullable=True)  # Made optional for simplified signup
    gender = Column(SQLEnum(Gender), nullable=True)  # Made optional for simplified signup
    marital_status = Column(
        SQLEnum(MaritalStatus), nullable=True
    )  # Made optional for simplified signup

    # Contact Information
    country_code = Column(String(5), nullable=True)  # Made optional for simplified signup
    mobile_number = Column(String(15), nullable=True)  # Made optional for simplified signup
    national_id = Column(String(50), nullable=True)

    # Family Information
    father_name = Column(String(127), nullable=True)  # Made optional for simplified signup
    mother_name = Column(String(127), nullable=True)  # Made optional for simplified signup
    spouse_name = Column(String(127), nullable=True)
    date_of_marriage = Column(Date, nullable=True)
    children = Column(JSON, nullable=True)  # Flexible JSON structure for children info

    # Location Information
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True, index=True)
    state_province = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True, index=True)
    postal_code = Column(String(20), nullable=True)

    # ISKCON Spiritual Information
    initiation_status = Column(
        SQLEnum(InitiationStatus),
        nullable=True,
        index=True,
        default=InitiationStatus.ASPIRING,
    )
    initiated_name = Column(
        String(127),
        nullable=True,
        comment="Spiritual name given at initiation (Harinam or Brahmin)",
    )
    spiritual_master = Column(String(255), nullable=True, index=True)
    initiation_date = Column(Date, nullable=True)
    initiation_place = Column(String(127), nullable=True)
    spiritual_guide = Column(String(127), nullable=True)

    # ISKCON Journey
    when_were_you_introduced_to_iskcon = Column(Date, nullable=True)
    who_introduced_you_to_iskcon = Column(String(127), nullable=True)
    which_iskcon_center_you_first_connected_to = Column(String(127), nullable=True)

    # Chanting Practice
    chanting_number_of_rounds = Column(Integer, nullable=True, default=16)
    chanting_16_rounds_since = Column(Date, nullable=True)

    # Devotional Education
    devotional_courses = Column(Text, nullable=True)

    # File Uploads
    profile_photo_path = Column(String(512), nullable=True)  # Profile photo relative path
    uploaded_files = Column(
        JSON, nullable=True
    )  # Array of file metadata: [{name, path, type, size, uploaded_at}]

    # System Fields
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.USER)
    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Performance optimization indexes
    __table_args__ = (
        Index("idx_city_country", "city", "country"),
        Index("idx_location_search", "country", "state_province", "city"),
        Index("idx_spiritual_info", "initiation_status", "spiritual_master"),
        Index("idx_name_search", "legal_name"),
        Index("idx_mobile_search", "country_code", "mobile_number"),
    )

    def __repr__(self):
        return f"<Devotee(id={self.id}, email={self.email}, legal_name={self.legal_name})>"


# User model removed - using Devotee model only for production


class Yatra(Base):
    """
    Yatra (pilgrimage) model for managing ISKCON yatras.

    This model captures all information about yatras including dates,
    pricing, itinerary, and registration management.
    """

    __tablename__ = "yatras"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Basic Information
    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    destination = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Dates
    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=False)
    registration_start_date = Column(Date, nullable=False)
    registration_deadline = Column(Date, nullable=False, index=True)

    # Pricing
    price_per_person = Column(Integer, nullable=False)
    child_discount_percentage = Column(Integer, default=0)

    # Details
    itinerary = Column(JSON, nullable=True)
    inclusions = Column(Text, nullable=True)
    exclusions = Column(Text, nullable=True)
    important_notes = Column(Text, nullable=True)
    terms_and_conditions = Column(Text, nullable=True)

    # Status
    status = Column(SQLEnum(YatraStatus), default=YatraStatus.DRAFT, index=True)
    is_featured = Column(Boolean, default=False)

    # Metadata
    created_by = Column(Integer, ForeignKey("devotees.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Soft delete
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Performance optimization indexes
    __table_args__ = (
        Index("idx_yatra_status_dates", "status", "start_date"),
        Index("idx_yatra_registration_open", "status", "registration_deadline"),
    )

    def __repr__(self):
        return f"<Yatra(id={self.id}, name={self.name}, destination={self.destination})>"


class YatraRegistration(Base):
    """
    Yatra registration model for managing devotee registrations.

    This model captures registration details, payment information,
    and tracks the registration workflow with audit trail.
    """

    __tablename__ = "yatra_registrations"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    registration_number = Column(String(50), unique=True, nullable=False, index=True)

    # Foreign Keys
    yatra_id = Column(
        Integer, ForeignKey("yatras.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    devotee_id = Column(
        Integer, ForeignKey("devotees.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    # Travel Details
    arrival_datetime = Column(DateTime(timezone=True), nullable=False)
    departure_datetime = Column(DateTime(timezone=True), nullable=False)
    arrival_mode = Column(String(50), nullable=True)
    departure_mode = Column(String(50), nullable=True)

    # Room Preferences
    room_preference = Column(SQLEnum(RoomPreference), nullable=False)
    ac_preference = Column(Boolean, default=False)
    floor_preference = Column(String(50), nullable=True)
    special_room_requests = Column(Text, nullable=True)

    # Members
    number_of_members = Column(Integer, nullable=False)
    accompanying_members = Column(JSON, nullable=True)

    # Payment
    total_amount = Column(Integer, nullable=False)
    payment_screenshot_path = Column(String(512), nullable=True)
    payment_reference = Column(String(100), nullable=True)
    payment_date = Column(DateTime(timezone=True), nullable=True)
    payment_method = Column(String(50), nullable=True)

    # Status & Workflow
    status = Column(SQLEnum(RegistrationStatus), default=RegistrationStatus.PENDING, index=True)
    status_history = Column(JSON, nullable=True)

    # Admin Actions
    admin_remarks = Column(Text, nullable=True)
    internal_notes = Column(Text, nullable=True)
    reviewed_by = Column(Integer, ForeignKey("devotees.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    confirmed_by = Column(Integer, ForeignKey("devotees.id"), nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)

    # User Input
    user_remarks = Column(Text, nullable=True)
    emergency_contact_name = Column(String(127), nullable=True)
    emergency_contact_number = Column(String(20), nullable=True)
    dietary_requirements = Column(Text, nullable=True)
    medical_conditions = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    submitted_at = Column(DateTime(timezone=True), nullable=True)

    # Soft delete
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Performance optimization indexes
    __table_args__ = (
        Index("idx_reg_yatra_devotee", "yatra_id", "devotee_id"),
        Index("idx_reg_status_yatra", "status", "yatra_id"),
        Index("idx_reg_devotee_status", "devotee_id", "status"),
        Index("idx_reg_number", "registration_number"),
    )

    def __repr__(self):
        return f"<YatraRegistration(id={self.id}, registration_number={self.registration_number}, status={self.status})>"


# --- Email normalization events ---
@event.listens_for(Devotee, "before_insert")
def normalize_devotee_email_before_insert(mapper, connection, target):  # type: ignore[misc]
    """Normalize email to lowercase before inserting."""
    if target.email:
        target.email = target.email.strip().lower()


@event.listens_for(Devotee, "before_update")
def normalize_devotee_email_before_update(mapper, connection, target):  # type: ignore[misc]
    """Normalize email to lowercase before updating."""
    if target.email:
        target.email = target.email.strip().lower()


# User model event listeners removed - using Devotee model only
