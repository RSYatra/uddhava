"""
Comprehensive Pydantic schemas for devotee management.

This module contains all the Pydantic models used for API request/response
validation and serialization for the enhanced devotee management system.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.password_validation import validate_password_strength
from app.db.models import Gender, InitiationStatus, MaritalStatus, UserRole


class ChildInfo(BaseModel):
    """Schema for child information."""

    name: str = Field(..., min_length=1, max_length=127)
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None

    model_config = ConfigDict(from_attributes=True)


class DevoteeBase(BaseModel):
    """Base devotee model with common fields."""

    # Personal Information
    legal_name: str = Field(
        ..., min_length=1, max_length=127, description="Legal full name"
    )
    date_of_birth: date = Field(..., description="Date of birth")
    gender: Gender = Field(..., description="Gender")
    marital_status: MaritalStatus = Field(..., description="Marital status")

    # Contact Information
    email: EmailStr = Field(..., description="Email address")
    country_code: str = Field(
        ...,
        min_length=1,
        max_length=5,
        description="Country code (e.g., 91 for India)",
    )
    mobile_number: str = Field(
        ...,
        min_length=10,
        max_length=15,
        description="Mobile number without country code",
    )
    national_id: Optional[str] = Field(
        None, max_length=50, description="National ID/Social Security Number"
    )

    # Family Information
    father_name: str = Field(
        ..., min_length=1, max_length=127, description="Father's name"
    )
    mother_name: str = Field(
        ..., min_length=1, max_length=127, description="Mother's name"
    )
    spouse_name: Optional[str] = Field(
        None, max_length=127, description="Spouse name (if married)"
    )
    date_of_marriage: Optional[date] = Field(
        None, description="Date of marriage (if applicable)"
    )

    # Location Information
    address: Optional[str] = Field(None, description="Full address")
    city: Optional[str] = Field(None, max_length=100, description="City")
    state_province: Optional[str] = Field(
        None, max_length=100, description="State or Province"
    )
    country: Optional[str] = Field(None, max_length=100, description="Country")
    postal_code: Optional[str] = Field(
        None, max_length=20, description="Postal/ZIP code"
    )

    # ISKCON Spiritual Information
    initiation_status: Optional[InitiationStatus] = Field(
        InitiationStatus.ASPIRING, description="Current initiation status"
    )
    spiritual_master: Optional[str] = Field(
        None, max_length=255, description="Name of spiritual master"
    )
    initiation_date: Optional[date] = Field(None, description="Date of initiation")
    initiation_place: Optional[str] = Field(
        None, max_length=127, description="Place of initiation"
    )
    spiritual_guide: Optional[str] = Field(
        None, max_length=127, description="Name of spiritual guide/mentor"
    )

    # ISKCON Journey
    when_were_you_introduced_to_iskcon: Optional[date] = Field(
        None, description="When were you first introduced to ISKCON"
    )
    who_introduced_you_to_iskcon: Optional[str] = Field(
        None, max_length=127, description="Who introduced you to ISKCON"
    )
    which_iskcon_center_you_first_connected_to: Optional[str] = Field(
        None,
        max_length=127,
        description="First ISKCON center you connected to",
    )

    # Chanting Practice
    chanting_number_of_rounds: Optional[int] = Field(
        16, ge=0, le=200, description="Current daily chanting rounds"
    )
    chanting_16_rounds_since: Optional[date] = Field(
        None, description="Date since chanting 16 rounds consistently"
    )

    # Devotional Education
    devotional_courses: Optional[str] = Field(
        None, description="Devotional courses completed (comma-separated)"
    )

    @field_validator("mobile_number")
    @classmethod
    def validate_mobile_number(cls, v):
        """Validate mobile number format."""
        # Remove any non-digit characters
        cleaned = "".join(c for c in v if c.isdigit())
        if len(cleaned) < 10 or len(cleaned) > 15:
            raise ValueError("Mobile number must be between 10-15 digits")
        return cleaned

    @field_validator("date_of_birth")
    @classmethod
    def validate_date_of_birth(cls, v):
        """Validate date of birth is reasonable."""
        if v and v > date.today():
            raise ValueError("Date of birth cannot be in the future")

        # Check if age is reasonable (between 5 and 120 years)
        today = date.today()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if age < 5 or age > 120:
            raise ValueError("Age must be between 5 and 120 years")

        return v

    @field_validator("date_of_marriage")
    @classmethod
    def validate_marriage_date(cls, v, values):
        """Validate marriage date against birth date and marital status."""
        if v:
            # Marriage date should be after birth date
            if "date_of_birth" in values.data and v <= values.data["date_of_birth"]:
                raise ValueError("Marriage date must be after birth date")

            # Marriage date shouldn't be in the future
            if v > date.today():
                raise ValueError("Marriage date cannot be in the future")

        return v


class DevoteeSimpleCreate(BaseModel):
    """Schema for simplified devotee signup with minimal required fields."""

    # Basic required fields for signup
    name: str = Field(..., min_length=1, max_length=127, description="Full name")
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password: min 8 chars, uppercase, lowercase, number, special char",
    )

    @field_validator("password")
    @classmethod
    def validate_password_strength_signup(cls, v):
        """Validate password strength requirements."""
        return validate_password_strength(v)

    model_config = ConfigDict(from_attributes=True)


class DevoteeCreate(DevoteeBase):
    """Schema for creating a devotee with full profile information."""

    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password: min 8 chars, uppercase, lowercase, number, special char",
    )
    children: Optional[List[ChildInfo]] = Field(
        None, description="List of children information"
    )

    @field_validator("password")
    @classmethod
    def validate_password_strength_signup(cls, v):
        """Validate password strength requirements."""
        return validate_password_strength(v)


class DevoteeUpdate(BaseModel):
    """Schema for updating devotee information."""

    # Personal Information (excluding email which shouldn't change easily)
    legal_name: Optional[str] = Field(None, min_length=1, max_length=127)
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    marital_status: Optional[MaritalStatus] = None

    # Contact Information
    country_code: Optional[str] = Field(None, min_length=1, max_length=5)
    mobile_number: Optional[str] = Field(None, min_length=10, max_length=15)
    national_id: Optional[str] = Field(None, max_length=50)

    # Family Information
    father_name: Optional[str] = Field(None, min_length=1, max_length=127)
    mother_name: Optional[str] = Field(None, min_length=1, max_length=127)
    spouse_name: Optional[str] = Field(None, max_length=127)
    date_of_marriage: Optional[date] = None
    children: Optional[List[ChildInfo]] = None

    # Location Information
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=100)
    state_province: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)

    # ISKCON Spiritual Information
    initiation_status: Optional[InitiationStatus] = None
    spiritual_master: Optional[str] = Field(None, max_length=255)
    initiation_date: Optional[date] = None
    initiation_place: Optional[str] = Field(None, max_length=127)
    spiritual_guide: Optional[str] = Field(None, max_length=127)

    # ISKCON Journey
    when_were_you_introduced_to_iskcon: Optional[date] = None
    who_introduced_you_to_iskcon: Optional[str] = Field(None, max_length=127)
    which_iskcon_center_you_first_connected_to: Optional[str] = Field(
        None, max_length=127
    )

    # Chanting Practice
    chanting_number_of_rounds: Optional[int] = Field(None, ge=0, le=200)
    chanting_16_rounds_since: Optional[date] = None

    # Devotional Education
    devotional_courses: Optional[str] = None

    @field_validator("mobile_number")
    @classmethod
    def validate_mobile_number(cls, v):
        """Validate mobile number format."""
        if v is not None:
            cleaned = "".join(c for c in v if c.isdigit())
            if len(cleaned) < 10 or len(cleaned) > 15:
                raise ValueError("Mobile number must be between 10-15 digits")
            return cleaned
        return v


class DevoteeOut(DevoteeBase):
    """Schema for devotee response (public information)."""

    id: int = Field(..., description="Devotee's unique identifier")
    role: UserRole = Field(default=UserRole.USER, description="User role")
    children: Optional[List[Dict[str, Any]]] = Field(
        None, description="Children information"
    )
    created_at: Optional[datetime] = Field(
        None, description="Account creation timestamp"
    )
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    # Computed fields
    full_name: Optional[str] = Field(None, description="Full display name")
    location_display: Optional[str] = Field(None, description="Formatted location")
    mobile_display: Optional[str] = Field(None, description="Formatted mobile number")
    children_count: Optional[int] = Field(None, description="Number of children")
    spiritual_journey_years: Optional[int] = Field(
        None, description="Years since introduction to ISKCON"
    )
    is_initiated: Optional[bool] = Field(
        None, description="Whether devotee is initiated"
    )
    is_brahmin_initiated: Optional[bool] = Field(
        None, description="Whether devotee has Brahmin initiation"
    )

    model_config = ConfigDict(from_attributes=True)


class DevoteeLogin(BaseModel):
    """Schema for devotee login."""

    email: EmailStr = Field(..., description="Devotee's email address")
    password: str = Field(
        ..., min_length=1, max_length=128, description="Devotee's password"
    )


class DevoteeSearchFilters(BaseModel):
    """Schema for devotee search filters."""

    # Text search
    search: Optional[str] = Field(
        None, max_length=255, description="Search in name, email, or location"
    )

    # Location filters
    country: Optional[str] = Field(None, max_length=100)
    state_province: Optional[str] = Field(None, max_length=100)
    city: Optional[str] = Field(None, max_length=100)

    # Spiritual filters
    initiation_status: Optional[InitiationStatus] = None
    spiritual_master: Optional[str] = Field(None, max_length=255)

    # Demographic filters
    gender: Optional[Gender] = None
    marital_status: Optional[MaritalStatus] = None

    # Age range filters
    min_age: Optional[int] = Field(None, ge=0, le=120)
    max_age: Optional[int] = Field(None, ge=0, le=120)

    # Chanting filters
    min_rounds: Optional[int] = Field(None, ge=0, le=200)
    max_rounds: Optional[int] = Field(None, ge=0, le=200)

    # Pagination
    page: int = Field(1, ge=1, description="Page number")
    limit: int = Field(50, ge=1, le=100, description="Items per page")

    # Sorting
    sort_by: Optional[str] = Field(
        "created_at",
        description="Sort field: legal_name, created_at, city, initiation_status",
    )
    sort_order: Optional[str] = Field(
        "desc", pattern="^(asc|desc)$", description="Sort order: asc or desc"
    )

    @field_validator("max_age")
    @classmethod
    def validate_age_range(cls, v, values):
        """Validate age range is logical."""
        if v is not None and "min_age" in values.data:
            min_age = values.data["min_age"]
            if min_age is not None and v < min_age:
                raise ValueError("max_age must be greater than or equal to min_age")
        return v

    @field_validator("max_rounds")
    @classmethod
    def validate_rounds_range(cls, v, values):
        """Validate chanting rounds range is logical."""
        if v is not None and "min_rounds" in values.data:
            min_rounds = values.data["min_rounds"]
            if min_rounds is not None and v < min_rounds:
                raise ValueError(
                    "max_rounds must be greater than or equal to min_rounds"
                )
        return v


class DevoteeListResponse(BaseModel):
    """Schema for paginated devotee list response."""

    devotees: List[DevoteeOut]
    total: int = Field(..., description="Total number of devotees matching filters")
    page: int = Field(..., description="Current page number")
    limit: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_prev: bool = Field(..., description="Whether there are previous pages")


class DevoteeStatsResponse(BaseModel):
    """Schema for devotee statistics."""

    total_devotees: int
    by_country: Dict[str, int]
    by_initiation_status: Dict[str, int]
    by_gender: Dict[str, int]
    by_marital_status: Dict[str, int]
    average_age: Optional[float]
    average_chanting_rounds: Optional[float]
    recently_joined: int  # In last 30 days


# Token schemas (reused from user schemas)
class Token(BaseModel):
    """Schema for JWT token response."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")


class TokenData(BaseModel):
    """Schema for token payload data."""

    email: Optional[str] = Field(None, description="Devotee email from token")


# Enhanced error response schemas
class ValidationErrorDetail(BaseModel):
    """Schema for validation error details."""

    field: str
    message: str
    invalid_value: Optional[Any] = None


class DetailedErrorResponse(BaseModel):
    """Schema for detailed error responses."""

    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(
        None, description="Error code for programmatic handling"
    )
    validation_errors: Optional[List[ValidationErrorDetail]] = Field(
        None, description="Field-specific validation errors"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)
