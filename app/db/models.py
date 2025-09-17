"""
SQLAlchemy database models.

This module contains all the database table definitions using SQLAlchemy ORM.
"""

from enum import Enum

from sqlalchemy import Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Integer, String, event
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class UserRole(str, Enum):
    """User roles enumeration."""

    USER = "USER"
    ADMIN = "ADMIN"


class User(Base):
    """User database model"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role: UserRole = Column(
        SQLEnum(UserRole, name="userrole"),
        nullable=False,
        default=UserRole.USER,
    )
    chanting_rounds = Column(Integer, nullable=True, default=16)
    photo = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"

    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == UserRole.ADMIN

    @property
    def is_user(self) -> bool:
        """Check if user has regular user role."""
        return self.role == UserRole.USER

    def can_access_user(self, user_id: int) -> bool:
        """Check if user can access another user's data."""
        return self.is_admin or self.id == user_id


# --- Email normalization events ---
@event.listens_for(User, "before_insert")
def normalize_email_before_insert(mapper, connection, target):  # type: ignore
    """Normalize email to lowercase before inserting."""
    if target.email:
        target.email = target.email.strip().lower()


@event.listens_for(User, "before_update")
def normalize_email_before_update(mapper, connection, target):  # type: ignore
    """Normalize email to lowercase before updating."""
    if target.email:
        target.email = target.email.strip().lower()
