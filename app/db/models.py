"""
SQLAlchemy database models.

This module contains database table definitions for authentication and family management.
"""

from enum import Enum

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
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


class Devotee(Base):
    """
    User account model for authentication.

    Stores primary account holder information with minimal fields required for signup.
    Family members are managed separately and linked to this account.
    """

    __tablename__ = "devotees"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Authentication
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    legal_name = Column(String(127), nullable=False)

    # Email verification
    email_verified = Column(Boolean, nullable=False, default=False)
    verification_token = Column(String(255), nullable=True)
    verification_expires = Column(DateTime(timezone=True), nullable=True)

    # Password reset
    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)

    # System fields
    role = Column(String(50), nullable=False, default=UserRole.USER.value)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Devotee(id={self.id}, email={self.email}, legal_name={self.legal_name})>"


class FamilyMember(Base):
    """
    Family member linked to a devotee account.

    Allows account holders to add family members without requiring separate signup.
    These members can later participate in events.
    """

    __tablename__ = "family_members"

    id = Column(Integer, primary_key=True, index=True)
    devotee_id = Column(
        Integer, ForeignKey("devotees.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Personal Information
    legal_name = Column(String(127), nullable=False)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(1), nullable=True)  # 'M' or 'F'

    # Contact Information
    mobile_number = Column(String(15), nullable=True)
    email = Column(String(255), nullable=True)

    # Relationship to primary account holder
    relationship = Column(String(50), nullable=True)  # e.g., 'spouse', 'child', 'parent'

    # System fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<FamilyMember(id={self.id}, devotee_id={self.devotee_id}, name={self.legal_name})>"
