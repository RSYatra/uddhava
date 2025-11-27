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
    """Room preference enumeration."""

    SINGLE = "SINGLE"
    DOUBLE_SHARING = "DOUBLE_SHARING"
    TRIPLE_SHARING = "TRIPLE_SHARING"
    QUAD_SHARING = "QUAD_SHARING"
    DORMITORY = "DORMITORY"


class RoomCategory(str, Enum):
    """Room category enumeration for yatra pricing."""

    SHARED_AC = "SHARED_AC"
    SHARED_NON_AC = "SHARED_NON_AC"
    PRIVATE_AC = "PRIVATE_AC"
    PRIVATE_NON_AC = "PRIVATE_NON_AC"
    FAMILY_AC = "FAMILY_AC"
    FAMILY_NON_AC = "FAMILY_NON_AC"


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


class PricingTemplate(Base):
    """
    Reusable pricing template for yatras.

    This model stores pricing configurations that can be reused across
    multiple yatras, ensuring consistency and easy management.
    """

    __tablename__ = "pricing_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(127), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<PricingTemplate(id={self.id}, name={self.name})>"


class PricingTemplateDetail(Base):
    """
    Pricing details for each room category within a pricing template.

    Each template has 6 detail records (one per room category).
    """

    __tablename__ = "pricing_template_details"

    id = Column(Integer, primary_key=True)
    template_id = Column(Integer, ForeignKey("pricing_templates.id"), nullable=False)
    room_category = Column(SQLEnum(RoomCategory), nullable=False)
    price_per_person = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("template_id", "room_category", name="uq_template_room"),
        Index("idx_template_pricing", "template_id", "room_category"),
    )

    def __repr__(self):
        return f"<PricingTemplateDetail(id={self.id}, template_id={self.template_id}, room_category={self.room_category}, price={self.price_per_person})>"


class PaymentOption(Base):
    """
    Reusable payment option for yatras.

    This model stores payment methods (bank account or UPI) that can be
    reused across multiple yatras.
    """

    __tablename__ = "payment_options"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(127), nullable=False, unique=True)

    # Bank Details (nullable)
    bank_account_number = Column(String(50), nullable=True)
    ifsc_code = Column(String(20), nullable=True)
    bank_name = Column(String(100), nullable=True)
    branch_name = Column(String(100), nullable=True)
    account_holder_name = Column(String(127), nullable=True)
    account_type = Column(String(50), nullable=True)

    # UPI Details (nullable)
    upi_id = Column(String(100), nullable=True)
    upi_phone_number = Column(String(20), nullable=True)
    qr_code_path = Column(String(512), nullable=True)

    payment_method = Column(String(20), nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<PaymentOption(id={self.id}, name={self.name}, method={self.payment_method})>"


class YatraPaymentOption(Base):
    """
    Junction table linking yatras to payment options.

    This allows multiple payment options per yatra with display ordering.
    """

    __tablename__ = "yatra_payment_options"

    id = Column(Integer, primary_key=True)
    yatra_id = Column(Integer, ForeignKey("yatras.id"), nullable=False)
    payment_option_id = Column(Integer, ForeignKey("payment_options.id"), nullable=False)
    display_order = Column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint("yatra_id", "payment_option_id", name="uq_yatra_payment"),
        Index("idx_yatra_payment", "yatra_id"),
    )

    def __repr__(self):
        return f"<YatraPaymentOption(id={self.id}, yatra_id={self.yatra_id}, payment_option_id={self.payment_option_id})>"


class YatraMember(Base):
    """
    Individual member in a yatra registration.

    This model tracks each person in a group registration, including
    registered users and guest members.
    """

    __tablename__ = "yatra_members"

    id = Column(Integer, primary_key=True)
    registration_id = Column(Integer, ForeignKey("yatra_registrations.id"), nullable=False)
    devotee_id = Column(Integer, ForeignKey("devotees.id"), nullable=True)

    legal_name = Column(String(127), nullable=False)
    gender = Column(SQLEnum(Gender), nullable=False)
    date_of_birth = Column(Date, nullable=True)
    mobile_number = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)

    arrival_datetime = Column(DateTime(timezone=True), nullable=False)
    departure_datetime = Column(DateTime(timezone=True), nullable=False)
    room_category = Column(SQLEnum(RoomCategory), nullable=False)

    price_charged = Column(Integer, nullable=False)
    is_free = Column(Boolean, default=False)
    is_primary_registrant = Column(Boolean, default=False)
    is_registered_user = Column(Boolean, default=False)

    dietary_requirements = Column(String(255), nullable=True)
    medical_conditions = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_member_registration", "registration_id"),
        Index("idx_member_devotee", "devotee_id"),
    )

    def __repr__(self):
        return f"<YatraMember(id={self.id}, name={self.legal_name}, registration_id={self.registration_id})>"


class Yatra(Base):
    """
    Yatra (pilgrimage) model for managing ISKCON yatras.

    This model captures all information about yatras including dates,
    pricing template reference, itinerary, and registration management.
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

    # Pricing Template Reference
    pricing_template_id = Column(
        Integer, ForeignKey("pricing_templates.id"), nullable=False, index=True
    )

    # Capacity
    max_capacity = Column(Integer, nullable=True)

    # Details
    itinerary = Column(JSON, nullable=True)
    inclusions = Column(Text, nullable=True)
    exclusions = Column(Text, nullable=True)
    important_notes = Column(Text, nullable=True)
    terms_and_conditions = Column(Text, nullable=True)

    # Status
    status = Column(SQLEnum(YatraStatus), default=YatraStatus.DRAFT, index=True)
    is_featured = Column(Boolean, default=False)
    featured_until = Column(Date, nullable=True)

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

    This model now represents individual member registrations linked by group_id.
    Each member in a group has their own registration record.
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

    # Group Management
    group_id = Column(String(50), nullable=False, index=True)
    is_group_lead = Column(Boolean, default=True)

    # Payment (only for group lead)
    total_amount = Column(Integer, nullable=False)
    payment_screenshot_path = Column(String(512), nullable=True)
    payment_reference = Column(String(100), nullable=True)
    payment_date = Column(DateTime(timezone=True), nullable=True)
    payment_method = Column(String(50), nullable=True)

    # Status & Workflow
    status = Column(SQLEnum(RegistrationStatus), default=RegistrationStatus.PENDING, index=True)

    # Admin Actions
    admin_remarks = Column(Text, nullable=True)
    internal_notes = Column(Text, nullable=True)
    reviewed_by = Column(Integer, ForeignKey("devotees.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    confirmed_by = Column(Integer, ForeignKey("devotees.id"), nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)

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
        Index("idx_reg_group", "group_id"),
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
