"""
Pydantic schemas for yatra management.

This module contains schemas for yatra API request/response validation.
"""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.db.models import YatraStatus


class YatraBase(BaseModel):
    """Base yatra model with common fields."""

    name: str = Field(..., min_length=3, max_length=255)
    destination: str = Field(..., min_length=3, max_length=255)
    description: str | None = None
    start_date: date
    end_date: date
    registration_start_date: date
    registration_deadline: date
    price_per_person: int = Field(..., gt=0)
    child_discount_percentage: int = Field(default=0, ge=0, le=100)
    itinerary: list[dict[str, Any]] | None = None
    inclusions: str | None = None
    exclusions: str | None = None
    important_notes: str | None = None
    terms_and_conditions: str | None = None

    @field_validator("end_date")
    @classmethod
    def validate_end_after_start(cls, v: date, info: Any) -> date:
        if "start_date" in info.data and v <= info.data["start_date"]:
            raise ValueError("end_date must be after start_date")
        return v

    @field_validator("registration_deadline")
    @classmethod
    def validate_deadline_before_start(cls, v: date, info: Any) -> date:
        if "start_date" in info.data and v >= info.data["start_date"]:
            raise ValueError("registration_deadline must be before start_date")
        return v


class YatraCreate(YatraBase):
    """Schema for creating a new yatra."""

    pass


class YatraUpdate(BaseModel):
    """Schema for updating a yatra (all fields optional)."""

    name: str | None = Field(None, min_length=3, max_length=255)
    destination: str | None = Field(None, min_length=3, max_length=255)
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    registration_start_date: date | None = None
    registration_deadline: date | None = None
    price_per_person: int | None = Field(None, gt=0)
    child_discount_percentage: int | None = Field(None, ge=0, le=100)
    status: YatraStatus | None = None
    is_featured: bool | None = None
    itinerary: list[dict[str, Any]] | None = None
    inclusions: str | None = None
    exclusions: str | None = None
    important_notes: str | None = None
    terms_and_conditions: str | None = None


class YatraOut(YatraBase):
    """Schema for yatra response."""

    id: int
    slug: str
    status: YatraStatus
    is_featured: bool
    created_by: int
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class YatraWithStats(YatraOut):
    """Schema for yatra with registration statistics."""

    total_registrations: int
    confirmed_registrations: int
    is_registration_open: bool
