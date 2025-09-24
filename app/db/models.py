"""
SQLAlchemy database models.

This module contains all the database table definitions using SQLAlchemy ORM.
Enhanced devotee management system for ISKCON Radha Shyam Sundar Yatra.
"""

from datetime import date
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import (
    Index,
    Integer,
    String,
    Text,
    event,
)
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

    SINGLE = "SINGLE"
    MARRIED = "MARRIED"
    DIVORCED = "DIVORCED"
    WIDOWED = "WIDOWED"
    SEPARATED = "SEPARATED"
    OTHERS = "OTHERS"


class InitiationStatus(str, Enum):
    """ISKCON initiation status enumeration."""

    ASPIRING = "ASPIRING"
    HARINAM = "HARINAM"
    BRAHMIN = "BRAHMIN"


class Devotee(Base):
    """
    Comprehensive devotee model for ISKCON Radha Shyam Sundar Yatra.

    This model captures all essential information about devotees including
    personal details, spiritual journey, and ISKCON-specific information.
    Optimized for 100K users with strategic indexing.
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
    gender = Column(
        SQLEnum(Gender), nullable=True
    )  # Made optional for simplified signup
    marital_status = Column(
        SQLEnum(MaritalStatus), nullable=True
    )  # Made optional for simplified signup

    # Contact Information
    country_code = Column(
        String(5), nullable=True
    )  # Made optional for simplified signup
    mobile_number = Column(
        String(15), nullable=True
    )  # Made optional for simplified signup
    national_id = Column(String(50), nullable=True)

    # Family Information
    father_name = Column(
        String(127), nullable=True
    )  # Made optional for simplified signup
    mother_name = Column(
        String(127), nullable=True
    )  # Made optional for simplified signup
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
        return (
            f"<Devotee(id={self.id}, email={self.email}, legal_name={self.legal_name})>"
        )

    @property
    def is_admin(self) -> bool:
        """Check if devotee has admin role."""
        return self.role == UserRole.ADMIN

    @property
    def is_user(self) -> bool:
        """Check if devotee has regular user role."""
        return self.role == UserRole.USER

    def can_access_devotee(self, devotee_id: int) -> bool:
        """Check if devotee can access another devotee's data."""
        return self.is_admin or self.id == devotee_id

    @property
    def full_name(self) -> str:
        """Get devotee's full name."""
        return self.legal_name

    @property
    def display_name(self) -> str:
        """Get display name for UI purposes."""
        return self.legal_name

    @property
    def location_display(self) -> str:
        """Get formatted location string."""
        parts = []
        if self.city:
            parts.append(self.city)
        if self.state_province:
            parts.append(self.state_province)
        if self.country:
            parts.append(self.country)
        return ", ".join(parts) if parts else "Location not specified"

    @property
    def mobile_display(self) -> str:
        """Get formatted mobile number with country code."""
        if self.country_code and self.mobile_number:
            return f"+{self.country_code} {self.mobile_number}"
        return self.mobile_number or "Not provided"

    @property
    def children_count(self) -> int:
        """Get number of children."""
        if not self.children:
            return 0
        if isinstance(self.children, list):
            return len(self.children)
        if isinstance(self.children, dict) and "count" in self.children:
            return self.children.get("count", 0)
        return 0

    @property
    def spiritual_journey_years(self) -> Optional[int]:
        """Calculate years since introduction to ISKCON."""
        if not self.when_were_you_introduced_to_iskcon:
            return None
        today = date.today()
        return today.year - self.when_were_you_introduced_to_iskcon.year

    @property
    def is_initiated(self) -> bool:
        """Check if devotee is initiated (Harinam or Brahmin)."""
        return self.initiation_status in [
            InitiationStatus.HARINAM,
            InitiationStatus.BRAHMIN,
        ]

    @property
    def is_brahmin_initiated(self) -> bool:
        """Check if devotee has Brahmin initiation."""
        return self.initiation_status == InitiationStatus.BRAHMIN

    def get_children_info(self) -> List[Dict[str, Any]]:
        """Get structured children information."""
        if not self.children:
            return []

        if isinstance(self.children, list):
            return self.children

        if isinstance(self.children, dict):
            return self.children.get("children", [])

        return []

    def set_children_info(self, children_data: List[Dict[str, Any]]) -> None:
        """Set children information with proper structure."""
        self.children = {
            "count": len(children_data),
            "children": children_data,
            "updated_at": func.now(),
        }


# User model removed - using Devotee model only for production


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
