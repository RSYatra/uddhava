"""
Pydantic schemas for yatra members.

This module defines the request and response schemas for yatra member management.
"""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class YatraMemberBase(BaseModel):
    """Base schema for yatra member."""

    legal_name: str = Field(
        ...,
        max_length=127,
        description="Full legal name (required)",
        examples=["Radha Krishna Das"],
    )
    date_of_birth: date = Field(
        ...,
        description="Date of birth in YYYY-MM-DD format (required for age calculation)",
        examples=["1985-05-15"],
    )
    gender: Literal["M", "F", ""] = Field(
        ...,
        description="Gender: M (Male) or F (Female)",
        examples=["M"],
    )
    room_category: str = Field(
        ...,
        max_length=100,
        description="Room category name (must match available categories for yatra)",
        examples=["Deluxe AC Suite", "Economy Shared"],
    )
    room_preference: Literal["MALE_SHARING", "FEMALE_SHARING", "FAMILY", "FAMILY_WITH_CHILDREN"] = (
        Field(
            ...,
            description="Room preference: MALE_SHARING, FEMALE_SHARING, FAMILY, or FAMILY_WITH_CHILDREN",
            examples=["MALE_SHARING"],
        )
    )
    is_primary_registrant: bool = Field(
        ...,
        description="True for group lead, exactly one per group",
        examples=[True],
    )
    devotee_id: int | None = Field(
        None,
        description="Link to registered devotee (required for primary registrant)",
        examples=[83],
    )
    mobile_number: str | None = Field(
        None,
        min_length=10,
        max_length=15,
        description="Contact number (10-15 digits)",
        examples=["9876543210"],
    )
    email: EmailStr | None = Field(
        None,
        description="Valid email address",
        examples=["radha@example.com"],
    )
    dietary_requirements: str | None = Field(
        None,
        max_length=255,
        description="Special dietary needs",
        examples=["Vegetarian, no onion/garlic"],
    )
    medical_conditions: str | None = Field(
        None,
        max_length=255,
        description="Health information for organizers",
        examples=["Diabetic, requires insulin"],
    )
    arrival_datetime: datetime | None = Field(
        None,
        description="Arrival date and time (ISO 8601 format)",
        examples=["2025-11-21T10:00:00Z"],
    )
    departure_datetime: datetime | None = Field(
        None,
        description="Departure date and time (ISO 8601 format)",
        examples=["2026-03-21T18:00:00Z"],
    )


class YatraMemberCreate(YatraMemberBase):
    """Schema for creating a yatra member."""

    pass


class YatraMemberOut(YatraMemberBase):
    """Schema for yatra member output."""

    id: int = Field(..., description="Unique identifier for the member")
    registration_id: int = Field(..., description="ID of the registration this member belongs to")
    price_charged: int = Field(
        ..., description="Price charged for this member (snapshot at registration)"
    )
    created_at: datetime = Field(..., description="When the member was added to registration")
    updated_at: datetime | None = Field(
        None, description="When the member details were last updated"
    )

    class Config:
        from_attributes = True


class YatraMemberListResponse(BaseModel):
    """Schema for yatra member list response."""

    success: bool = True
    status_code: int = 200
    message: str = "Yatra members retrieved successfully"
    data: list[YatraMemberOut]
