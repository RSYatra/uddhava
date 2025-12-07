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
    UniqueConstraint,
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
    """Room preference enumeration for yatra registration."""

    MALE_SHARING = "MALE_SHARING"
    FEMALE_SHARING = "FEMALE_SHARING"
    FAMILY = "FAMILY"
    FAMILY_WITH_CHILDREN = "FAMILY_WITH_CHILDREN"


class PaymentMethod(str, Enum):
    """Payment method enumeration."""

    UPI = "UPI"
    BANK_TRANSFER = "BANK_TRANSFER"
    QR_CODE = "QR_CODE"
    CASH = "CASH"
    CHEQUE = "CHEQUE"


class PaymentStatus(str, Enum):
    """Payment status enumeration."""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


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


class RoomCategory(Base):
    """
    Room category with pricing for a specific yatra.

    Admin can create custom room categories per yatra with free-text names
    (e.g., "Deluxe AC Suite", "Economy Shared", "VIP Room").
    """

    __tablename__ = "room_categories"

    id = Column(Integer, primary_key=True, index=True)
    yatra_id = Column(
        Integer, ForeignKey("yatras.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name = Column(String(100), nullable=False)
    price_per_person = Column(Integer, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (UniqueConstraint("yatra_id", "name", name="unique_category_per_yatra"),)

    def __repr__(self):
        return f"<RoomCategory(id={self.id}, yatra_id={self.yatra_id}, name={self.name}, price={self.price_per_person})>"


class PaymentOption(Base):
    """
    Reusable payment option for yatras.

    This model stores payment methods (bank account, UPI, QR code) that can be
    reused across multiple yatras.
    """

    __tablename__ = "payment_options"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    method = Column(SQLEnum(PaymentMethod), nullable=False)

    # UPI Details
    upi_id = Column(String(100), nullable=True)

    # Bank Details
    account_holder = Column(String(255), nullable=True)
    account_number = Column(String(50), nullable=True)
    ifsc_code = Column(String(20), nullable=True)
    bank_name = Column(String(255), nullable=True)
    branch = Column(String(255), nullable=True)

    # QR Code
    qr_code_url = Column(Text, nullable=True)

    # General
    instructions = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<PaymentOption(id={self.id}, name={self.name}, method={self.method})>"


class YatraPaymentOption(Base):
    """
    Junction table linking yatras to payment options.

    This allows multiple payment options per yatra.
    """

    __tablename__ = "yatra_payment_options"

    id = Column(Integer, primary_key=True)
    yatra_id = Column(
        Integer, ForeignKey("yatras.id", ondelete="CASCADE"), nullable=False, index=True
    )
    payment_option_id = Column(
        Integer, ForeignKey("payment_options.id", ondelete="CASCADE"), nullable=False
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("yatra_id", "payment_option_id", name="unique_payment_per_yatra"),
    )

    def __repr__(self):
        return f"<YatraPaymentOption(id={self.id}, yatra_id={self.yatra_id}, payment_option_id={self.payment_option_id})>"


class YatraMember(Base):
    """
    Individual member in a yatra registration.

    This model tracks each person in a group registration, including
    registered users and guest members. Room category is stored as VARCHAR
    to support custom category names per yatra.
    """

    __tablename__ = "yatra_members"

    id = Column(Integer, primary_key=True)
    registration_id = Column(
        Integer,
        ForeignKey("yatra_registrations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    devotee_id = Column(
        Integer, ForeignKey("devotees.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Personal Information
    legal_name = Column(String(127), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    gender = Column(SQLEnum(Gender), nullable=False)
    mobile_number = Column(String(15), nullable=True)
    email = Column(String(255), nullable=True)

    # Room Information
    room_category = Column(String(100), nullable=False)
    room_preference = Column(SQLEnum(RoomPreference), nullable=False)

    # Registration Details
    is_primary_registrant = Column(Boolean, default=False)
    price_charged = Column(Integer, nullable=False)

    # Travel Details
    arrival_datetime = Column(DateTime(timezone=True), nullable=True)
    departure_datetime = Column(DateTime(timezone=True), nullable=True)

    # Special Requirements
    dietary_requirements = Column(String(255), nullable=True)
    medical_conditions = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<YatraMember(id={self.id}, name={self.legal_name}, registration_id={self.registration_id})>"


class Yatra(Base):
    """
    Yatra (pilgrimage) model for managing ISKCON yatras.

    Simplified model without pricing templates, max capacity, or featured flags.
    Room categories and pricing are managed separately per yatra.
    """

    __tablename__ = "yatras"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Basic Information
    name = Column(String(255), nullable=False, index=True)
    destination = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Dates
    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=False)
    registration_deadline = Column(Date, nullable=False, index=True)

    # Details
    itinerary = Column(Text, nullable=True)
    terms_and_conditions = Column(Text, nullable=True)

    # Status
    is_active = Column(Boolean, default=True, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Yatra(id={self.id}, name={self.name}, destination={self.destination})>"


class YatraRegistration(Base):
    """
    Yatra registration model for managing devotee registrations.

    Simplified model with group_id in format GRP-{year}-{yatra_id}-{sequence}.
    Each registration represents one devotee's registration, linked to members via group_id.
    """

    __tablename__ = "yatra_registrations"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    yatra_id = Column(
        Integer, ForeignKey("yatras.id", ondelete="CASCADE"), nullable=False, index=True
    )
    devotee_id = Column(
        Integer, ForeignKey("devotees.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Group Management (format: GRP-2026-1-001)
    group_id = Column(String(50), nullable=False, index=True)
    is_group_lead = Column(Boolean, default=True)

    # Payment Information
    payment_option_id = Column(Integer, ForeignKey("payment_options.id"), nullable=False)
    payment_amount = Column(Integer, nullable=False)
    payment_status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING, index=True)

    # Registration Status
    status = Column(SQLEnum(RegistrationStatus), default=RegistrationStatus.PENDING, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<YatraRegistration(id={self.id}, group_id={self.group_id}, status={self.status})>"


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
