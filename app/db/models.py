"""
SQLAlchemy database models.

This module contains all the database table definitions using SQLAlchemy ORM.
"""

from sqlalchemy import Column, DateTime, Integer, String, event
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class User(Base):
    """User database model"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    chanting_rounds = Column(Integer, nullable=False)
    photo = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"


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
