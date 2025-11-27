"""
Pydantic schemas for yatra management.

This module contains schemas for yatra API request/response validation.
"""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.db.models import YatraStatus
from app.schemas.payment_option import PaymentOptionOut
from app.schemas.pricing_template import PricingTemplateOut


class YatraBase(BaseModel):
    """Base yatra model with common fields (no validators for output schemas)."""

    name: str = Field(..., min_length=3, max_length=255)
    destination: str = Field(..., min_length=3, max_length=255)
    description: str | None = None
    start_date: date
    end_date: date
    registration_start_date: date
    registration_deadline: date
    itinerary: list[dict[str, Any]] | None = None
    inclusions: str | None = None
    exclusions: str | None = None
    important_notes: str | None = None
    terms_and_conditions: str | None = None


class YatraCreate(YatraBase):
    """Schema for creating a new yatra with validation."""

    pricing_template_id: int = Field(..., gt=0)
    payment_option_ids: list[int] = Field(..., min_length=1)
    max_capacity: int | None = Field(None, gt=0)
    is_featured: bool = False
    featured_until: date | None = None

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


class YatraUpdate(BaseModel):
    """Schema for updating a yatra (all fields optional)."""

    name: str | None = Field(None, min_length=3, max_length=255)
    destination: str | None = Field(None, min_length=3, max_length=255)
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    registration_start_date: date | None = None
    registration_deadline: date | None = None
    pricing_template_id: int | None = Field(None, gt=0)
    payment_option_ids: list[int] | None = Field(None, min_length=1)
    max_capacity: int | None = Field(None, gt=0)
    status: YatraStatus | None = None
    is_featured: bool | None = None
    featured_until: date | None = None
    itinerary: list[dict[str, Any]] | None = None
    inclusions: str | None = None
    exclusions: str | None = None
    important_notes: str | None = None
    terms_and_conditions: str | None = None


class YatraOut(YatraBase):
    """Schema for yatra response."""

    id: int
    slug: str
    pricing_template_id: int
    max_capacity: int | None
    status: YatraStatus
    is_featured: bool
    featured_until: date | None
    created_by: int
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class YatraDetailOut(YatraOut):
    """Schema for detailed yatra response with pricing and payment options."""

    pricing_template: PricingTemplateOut | None = None
    payment_options: list[PaymentOptionOut] = []
