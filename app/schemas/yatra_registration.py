"""
Pydantic schemas for yatra registration management.

This module contains schemas for registration API request/response validation.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.db.models import RegistrationStatus
from app.schemas.payment_option import PaymentOptionOut
from app.schemas.yatra_member import YatraMemberCreate, YatraMemberOut


class RegistrationCreate(BaseModel):
    """Schema for creating a new group registration."""

    yatra_id: int
    members: list[YatraMemberCreate] = Field(..., min_length=1)

    @field_validator("members")
    @classmethod
    def validate_primary_registrant(cls, v: list[YatraMemberCreate]) -> list[YatraMemberCreate]:
        """Ensure exactly one primary registrant exists."""
        primary_count = sum(1 for member in v if member.is_primary_registrant)
        if primary_count != 1:
            raise ValueError("Exactly one member must be marked as primary registrant")

        # Ensure primary registrant has devotee_id
        primary = next(m for m in v if m.is_primary_registrant)
        if not primary.devotee_id:
            raise ValueError("Primary registrant must be a registered user (devotee_id required)")

        return v


class RegistrationUpdate(BaseModel):
    """Schema for updating a registration (only allowed in PENDING status)."""

    payment_reference: str | None = None
    payment_method: str | None = None


class RegistrationOut(BaseModel):
    """Schema for registration response."""

    id: int
    registration_number: str
    yatra_id: int
    devotee_id: int
    group_id: str
    is_group_lead: bool
    total_amount: int
    payment_screenshot_path: str | None
    payment_reference: str | None
    payment_date: datetime | None
    payment_method: str | None
    status: RegistrationStatus
    admin_remarks: str | None
    internal_notes: str | None
    created_at: datetime
    updated_at: datetime | None
    submitted_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class GroupRegistrationOut(BaseModel):
    """Schema for group registration response with members."""

    group_id: str
    registrations: list[RegistrationOut]
    members: list[YatraMemberOut]
    total_amount: int
    payment_options: list[PaymentOptionOut] = []


class StatusUpdateRequest(BaseModel):
    """Schema for admin status update."""

    status: RegistrationStatus
    admin_remarks: str | None = Field(None, max_length=1000)
