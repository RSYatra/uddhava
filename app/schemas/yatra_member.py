"""
Pydantic schemas for yatra members.

This module defines the request and response schemas for yatra member management.
"""

from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field

from app.db.models import Gender, RoomCategory


class YatraMemberCreate(BaseModel):
    """Schema for creating a yatra member."""

    devotee_id: int | None = None
    legal_name: str = Field(..., min_length=1, max_length=127)
    gender: Gender
    date_of_birth: date | None = None
    mobile_number: str | None = Field(None, max_length=20)
    email: EmailStr | None = None

    arrival_datetime: datetime
    departure_datetime: datetime
    room_category: RoomCategory

    is_primary_registrant: bool = False
    dietary_requirements: str | None = Field(None, max_length=255)
    medical_conditions: str | None = Field(None, max_length=255)


class YatraMemberOut(BaseModel):
    """Schema for yatra member output."""

    id: int
    registration_id: int
    devotee_id: int | None
    legal_name: str
    gender: Gender
    date_of_birth: date | None
    mobile_number: str | None
    email: str | None

    arrival_datetime: datetime
    departure_datetime: datetime
    room_category: RoomCategory

    price_charged: int
    is_free: bool
    is_primary_registrant: bool
    is_registered_user: bool

    dietary_requirements: str | None
    medical_conditions: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class YatraMemberListResponse(BaseModel):
    """Schema for yatra member list response."""

    success: bool = True
    status_code: int = 200
    message: str = "Yatra members retrieved successfully"
    data: list[YatraMemberOut]
