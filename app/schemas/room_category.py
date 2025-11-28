"""
Room category schemas for yatra pricing.

This module defines Pydantic schemas for room categories, which are
custom pricing categories created per yatra by admins.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class RoomCategoryBase(BaseModel):
    """Base schema for room category."""

    name: str = Field(
        ...,
        max_length=100,
        description="Room category name (e.g., 'Deluxe AC Suite', 'Economy Shared')",
        examples=["Deluxe AC Suite", "Economy Shared", "VIP Room"],
    )
    price_per_person: int = Field(
        ...,
        gt=0,
        description="Price per person in this category (in rupees, integer only)",
        examples=[5000, 8000, 12000],
    )
    description: str | None = Field(
        None,
        max_length=500,
        description="Optional description of the room category",
        examples=["Spacious AC room with attached bathroom and balcony"],
    )


class RoomCategoryCreate(RoomCategoryBase):
    """Schema for creating a new room category."""

    pass


class RoomCategoryUpdate(BaseModel):
    """Schema for updating an existing room category."""

    name: str | None = Field(None, max_length=100, description="Updated room category name")
    price_per_person: int | None = Field(
        None, gt=0, description="Updated price per person (integer only)"
    )
    description: str | None = Field(None, max_length=500, description="Updated description")
    is_active: bool | None = Field(None, description="Whether the category is active")


class RoomCategoryOut(RoomCategoryBase):
    """Schema for room category output."""

    id: int = Field(..., description="Unique identifier for the room category")
    yatra_id: int = Field(..., description="ID of the yatra this category belongs to")
    is_active: bool = Field(..., description="Whether the category is active")
    created_at: datetime = Field(..., description="When the category was created")
    updated_at: datetime = Field(..., description="When the category was last updated")

    class Config:
        from_attributes = True
