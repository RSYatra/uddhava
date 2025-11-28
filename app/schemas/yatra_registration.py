"""
Pydantic schemas for yatra registration management.

This module contains schemas for registration API request/response validation.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.db.models import PaymentStatus, RegistrationStatus
from app.schemas.yatra_member import YatraMemberCreate, YatraMemberOut


class RegistrationCreate(BaseModel):
    """
    Schema for creating a new group registration.

    **REQUIRED FIELDS:**
    - yatra_id (integer): ID of the yatra to register for
    - members (array): List of members (minimum 1, maximum 20)
    - payment_option_id (integer): Selected payment option ID

    **VALIDATION RULES:**
    - Exactly one member must have is_primary_registrant = true
    - Primary registrant must have devotee_id (must be registered user)
    - All members must have valid date_of_birth for age calculation
    """

    yatra_id: int = Field(..., description="ID of the yatra to register for")
    members: list[YatraMemberCreate] = Field(
        ...,
        min_length=1,
        max_length=20,
        description="List of members (1-20 people)",
    )
    payment_option_id: int = Field(..., description="Selected payment option ID")

    @field_validator("members")
    @classmethod
    def validate_primary_registrant(cls, v: list[YatraMemberCreate]) -> list[YatraMemberCreate]:
        """Ensure exactly one primary registrant exists and has devotee_id."""
        primary_count = sum(1 for member in v if member.is_primary_registrant)
        if primary_count != 1:
            raise ValueError("Exactly one member must be marked as primary registrant")

        # Ensure primary registrant has devotee_id
        primary = next(m for m in v if m.is_primary_registrant)
        if not primary.devotee_id:
            raise ValueError("Primary registrant must be a registered user (devotee_id required)")

        return v


class RegistrationUpdate(BaseModel):
    """Schema for updating a registration (limited fields)."""

    status: RegistrationStatus | None = Field(None, description="Updated registration status")
    payment_status: PaymentStatus | None = Field(None, description="Updated payment status")


class RegistrationOut(BaseModel):
    """Schema for registration response."""

    id: int = Field(..., description="Unique registration ID")
    yatra_id: int = Field(..., description="ID of the yatra")
    devotee_id: int = Field(..., description="ID of the devotee who created the registration")
    group_id: str = Field(..., description="Group ID in format GRP-{year}-{yatra_id}-{sequence}")
    is_group_lead: bool = Field(..., description="Whether this devotee is the group lead")
    payment_option_id: int = Field(..., description="Selected payment option ID")
    payment_amount: int = Field(..., description="Total payment amount for the group")
    payment_status: PaymentStatus = Field(..., description="Payment status")
    status: RegistrationStatus = Field(..., description="Registration status")
    created_at: datetime = Field(..., description="When the registration was created")
    updated_at: datetime | None = Field(None, description="When the registration was last updated")

    model_config = ConfigDict(from_attributes=True)


class GroupRegistrationOut(BaseModel):
    """Schema for group registration response with members."""

    group_id: str = Field(..., description="Group ID")
    yatra_id: int = Field(..., description="Yatra ID")
    yatra_name: str = Field(..., description="Yatra name")
    registrations: list[RegistrationOut] = Field(
        ..., description="List of registrations in this group"
    )
    members: list[YatraMemberOut] = Field(..., description="List of all members in this group")
    total_amount: int = Field(..., description="Total amount for the entire group")
    payment_status: PaymentStatus = Field(..., description="Overall payment status")
    status: RegistrationStatus = Field(..., description="Overall registration status")


class StatusUpdateRequest(BaseModel):
    """Schema for admin status update."""

    status: RegistrationStatus = Field(..., description="New registration status")
    payment_status: PaymentStatus | None = Field(None, description="New payment status (optional)")
