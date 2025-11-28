"""
Pydantic schemas for yatra management.

This module contains schemas for yatra API request/response validation.
"""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.payment_option import PaymentOptionOut
from app.schemas.room_category import RoomCategoryOut


class YatraBase(BaseModel):
    """Base yatra model with common fields."""

    name: str = Field(..., min_length=3, max_length=255, description="Yatra name")
    destination: str = Field(..., min_length=3, max_length=255, description="Destination location")
    description: str | None = Field(None, description="Detailed description of the yatra")
    start_date: date = Field(..., description="Yatra start date (YYYY-MM-DD)")
    end_date: date = Field(..., description="Yatra end date (YYYY-MM-DD)")
    registration_deadline: date = Field(..., description="Last date for registration (YYYY-MM-DD)")
    itinerary: str | None = Field(None, description="Detailed itinerary text")
    terms_and_conditions: str | None = Field(None, description="Terms and conditions text")


class YatraCreate(YatraBase):
    """
    Schema for creating a new yatra with validation.

    **REQUIRED FIELDS:**
    - name (string, 3-255 chars): Yatra name
    - destination (string, 3-255 chars): Destination location
    - start_date (date, YYYY-MM-DD): Yatra start date (must be in future)
    - end_date (date, YYYY-MM-DD): Yatra end date (must be after start_date, within 30 days)
    - registration_deadline (date, YYYY-MM-DD): Registration deadline (must be before end_date)

    **OPTIONAL FIELDS:**
    - description (string): Detailed description
    - itinerary (string): Detailed itinerary
    - terms_and_conditions (string): Terms and conditions

    **VALIDATION RULES:**
    1. start_date must be in the future (> today)
    2. end_date must be in the future (> today)
    3. registration_deadline must be in the future (> today)
    4. end_date must be after start_date
    5. Duration (end_date - start_date) must be <= 30 days
    6. registration_deadline must be before end_date

    **NOTE:**
    - Room categories and pricing are added separately via /yatras/{id}/room-categories endpoint
    - Payment options are added separately via yatra payment options endpoint
    """

    @field_validator("start_date")
    @classmethod
    def validate_start_date_future(cls, v: date) -> date:
        from datetime import date as date_class

        today = date_class.today()
        if v <= today:
            raise ValueError("start_date must be in the future")
        return v

    @field_validator("end_date")
    @classmethod
    def validate_end_date(cls, v: date, info: Any) -> date:
        from datetime import date as date_class

        today = date_class.today()

        # Must be in future
        if v <= today:
            raise ValueError("end_date must be in the future")

        # Must be after start_date
        if "start_date" in info.data and v <= info.data["start_date"]:
            raise ValueError("end_date must be after start_date")

        # Duration must be <= 30 days
        if "start_date" in info.data:
            duration = (v - info.data["start_date"]).days
            if duration > 30:
                raise ValueError("yatra duration (end_date - start_date) must be 30 days or less")

        return v

    @field_validator("registration_deadline")
    @classmethod
    def validate_registration_deadline(cls, v: date, info: Any) -> date:
        from datetime import date as date_class

        today = date_class.today()

        # Must be in future
        if v <= today:
            raise ValueError("registration_deadline must be in the future")

        # Must be before end_date
        if "end_date" in info.data and v >= info.data["end_date"]:
            raise ValueError("registration_deadline must be before end_date")

        return v


class YatraUpdate(BaseModel):
    """
    Schema for updating a yatra (all fields optional).

    **OPTIONAL FIELDS:**
    - name (string, 3-255 chars): Updated yatra name
    - destination (string, 3-255 chars): Updated destination
    - description (string): Updated description
    - start_date (date, YYYY-MM-DD): Updated start date
    - end_date (date, YYYY-MM-DD): Updated end date
    - registration_deadline (date, YYYY-MM-DD): Updated registration deadline
    - itinerary (string): Updated itinerary
    - terms_and_conditions (string): Updated terms and conditions
    - is_active (boolean): Whether the yatra is active

    **VALIDATION RULES:**
    - If updating dates, same validation rules apply as create
    - Cannot update yatra that has already started (checked in service layer)
    """

    name: str | None = Field(None, min_length=3, max_length=255)
    destination: str | None = Field(None, min_length=3, max_length=255)
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    registration_deadline: date | None = None
    itinerary: str | None = None
    terms_and_conditions: str | None = None
    is_active: bool | None = None


class YatraOut(YatraBase):
    """Schema for yatra response."""

    id: int = Field(..., description="Unique yatra ID")
    is_active: bool = Field(..., description="Whether the yatra is active")
    created_at: datetime = Field(..., description="When the yatra was created")
    updated_at: datetime | None = Field(None, description="When the yatra was last updated")

    model_config = ConfigDict(from_attributes=True)


class YatraDetailOut(YatraOut):
    """Schema for detailed yatra response with room categories and payment options."""

    room_categories: list[RoomCategoryOut] = Field(
        default_factory=list, description="Available room categories with pricing"
    )
    payment_options: list[PaymentOptionOut] = Field(
        default_factory=list, description="Available payment options"
    )
