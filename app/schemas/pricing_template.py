"""
Pydantic schemas for pricing templates.

This module defines the request and response schemas for pricing template management.
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.db.models import RoomCategory


class PricingTemplateDetailCreate(BaseModel):
    """Schema for creating a pricing template detail."""

    room_category: RoomCategory
    price_per_person: int = Field(..., gt=0, description="Price per person in rupees")


class PricingTemplateDetailOut(BaseModel):
    """Schema for pricing template detail output."""

    id: int
    template_id: int
    room_category: RoomCategory
    price_per_person: int

    class Config:
        from_attributes = True


class PricingTemplateCreate(BaseModel):
    """Schema for creating a pricing template."""

    name: str = Field(..., min_length=1, max_length=127)
    description: str | None = None
    pricing_details: list[PricingTemplateDetailCreate] = Field(
        ..., min_length=6, max_length=6, description="Must include all 6 room categories"
    )

    @field_validator("pricing_details")
    @classmethod
    def validate_all_categories(
        cls, v: list[PricingTemplateDetailCreate]
    ) -> list[PricingTemplateDetailCreate]:
        """Ensure all 6 room categories are present."""
        categories = {detail.room_category for detail in v}
        required_categories = {
            RoomCategory.SHARED_AC,
            RoomCategory.SHARED_NON_AC,
            RoomCategory.PRIVATE_AC,
            RoomCategory.PRIVATE_NON_AC,
            RoomCategory.FAMILY_AC,
            RoomCategory.FAMILY_NON_AC,
        }
        if categories != required_categories:
            missing = required_categories - categories
            raise ValueError(f"Missing room categories: {missing}")
        return v


class PricingTemplateUpdate(BaseModel):
    """Schema for updating a pricing template."""

    name: str | None = Field(None, min_length=1, max_length=127)
    description: str | None = None
    is_active: bool | None = None
    pricing_details: list[PricingTemplateDetailCreate] | None = Field(
        None, min_length=6, max_length=6, description="Must include all 6 room categories"
    )

    @field_validator("pricing_details")
    @classmethod
    def validate_all_categories(
        cls, v: list[PricingTemplateDetailCreate] | None
    ) -> list[PricingTemplateDetailCreate] | None:
        """Ensure all 6 room categories are present if provided."""
        if v is None:
            return v
        categories = {detail.room_category for detail in v}
        required_categories = {
            RoomCategory.SHARED_AC,
            RoomCategory.SHARED_NON_AC,
            RoomCategory.PRIVATE_AC,
            RoomCategory.PRIVATE_NON_AC,
            RoomCategory.FAMILY_AC,
            RoomCategory.FAMILY_NON_AC,
        }
        if categories != required_categories:
            missing = required_categories - categories
            raise ValueError(f"Missing room categories: {missing}")
        return v


class PricingTemplateOut(BaseModel):
    """Schema for pricing template output."""

    id: int
    name: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime | None
    pricing_details: list[PricingTemplateDetailOut]

    class Config:
        from_attributes = True


class PricingTemplateListResponse(BaseModel):
    """Schema for pricing template list response."""

    success: bool = True
    status_code: int = 200
    message: str = "Pricing templates retrieved successfully"
    data: list[PricingTemplateOut]
