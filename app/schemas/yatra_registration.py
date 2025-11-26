"""
Pydantic schemas for yatra registration management.

This module contains schemas for registration API request/response validation.
"""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.db.models import Gender, RegistrationStatus, RoomPreference


class AccompanyingMember(BaseModel):
    """Schema for accompanying member information."""

    name: str = Field(..., min_length=2, max_length=127)
    date_of_birth: date
    gender: Gender
    relation: str | None = Field(None, max_length=50)

    @field_validator("date_of_birth")
    @classmethod
    def validate_age(cls, v: date) -> date:
        age = (date.today() - v).days / 365.25
        if age < 5:
            raise ValueError("Children below 5 years should not be included")
        return v


class RegistrationCreate(BaseModel):
    """Schema for creating a new registration."""

    yatra_id: int
    arrival_datetime: datetime
    departure_datetime: datetime
    arrival_mode: str | None = Field(None, max_length=50)
    departure_mode: str | None = Field(None, max_length=50)
    room_preference: RoomPreference
    ac_preference: bool = False
    floor_preference: str | None = Field(None, max_length=50)
    special_room_requests: str | None = Field(None, max_length=500)
    number_of_members: int = Field(..., ge=1, le=20)
    accompanying_members: list[AccompanyingMember] = []
    user_remarks: str | None = Field(None, max_length=1000)
    emergency_contact_name: str | None = Field(None, max_length=127)
    emergency_contact_number: str | None = Field(None, max_length=20)
    dietary_requirements: str | None = Field(None, max_length=500)
    medical_conditions: str | None = Field(None, max_length=500)

    @field_validator("accompanying_members")
    @classmethod
    def validate_member_count(
        cls, v: list[AccompanyingMember], info: Any
    ) -> list[AccompanyingMember]:
        if "number_of_members" in info.data:
            expected = info.data["number_of_members"] - 1
            if len(v) != expected:
                raise ValueError(
                    f"Number of accompanying members ({len(v)}) must match "
                    f"number_of_members - 1 ({expected})"
                )
        return v

    @field_validator("departure_datetime")
    @classmethod
    def validate_departure_after_arrival(cls, v: datetime, info: Any) -> datetime:
        if "arrival_datetime" in info.data and v <= info.data["arrival_datetime"]:
            raise ValueError("departure_datetime must be after arrival_datetime")
        return v


class RegistrationUpdate(BaseModel):
    """Schema for updating a registration (only allowed in PENDING status)."""

    arrival_datetime: datetime | None = None
    departure_datetime: datetime | None = None
    arrival_mode: str | None = Field(None, max_length=50)
    departure_mode: str | None = Field(None, max_length=50)
    room_preference: RoomPreference | None = None
    ac_preference: bool | None = None
    floor_preference: str | None = None
    special_room_requests: str | None = None
    user_remarks: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_number: str | None = None
    dietary_requirements: str | None = None
    medical_conditions: str | None = None


class RegistrationOut(BaseModel):
    """Schema for registration response."""

    id: int
    registration_number: str
    yatra_id: int
    devotee_id: int
    arrival_datetime: datetime
    departure_datetime: datetime
    arrival_mode: str | None
    departure_mode: str | None
    room_preference: RoomPreference
    ac_preference: bool
    floor_preference: str | None
    special_room_requests: str | None
    number_of_members: int
    accompanying_members: list[dict[str, Any]] | None
    total_amount: int
    payment_screenshot_path: str | None
    payment_reference: str | None
    payment_date: datetime | None
    payment_method: str | None
    status: RegistrationStatus
    admin_remarks: str | None
    user_remarks: str | None
    emergency_contact_name: str | None
    emergency_contact_number: str | None
    dietary_requirements: str | None
    medical_conditions: str | None
    created_at: datetime
    updated_at: datetime | None
    submitted_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class StatusUpdateRequest(BaseModel):
    """Schema for admin status update."""

    status: RegistrationStatus
    admin_remarks: str | None = Field(None, max_length=1000)
