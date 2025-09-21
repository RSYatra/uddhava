"""
Pydantic schemas for request and response models.

This module contains all the Pydantic models used for API request/response
validation and serialization.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.password_validation import validate_password_strength


class UserBase(BaseModel):
    """Base user model with common fields."""

    name: str = Field(..., min_length=1, max_length=255, description="User's full name")
    email: EmailStr = Field(..., description="User's email address")
    chanting_rounds: Optional[int] = Field(
        default=16,
        ge=0,
        le=200,
        description="Daily chanting rounds (default: 16, optional)",
    )


class UserCreate(UserBase):
    """Schema for creating a user via form (legacy endpoint)."""

    pass


class UserSignup(UserBase):
    """Schema for user registration."""

    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password: min 8 chars, uppercase, lowercase, number, special char",
    )

    @field_validator("password")
    @classmethod
    def validate_password_strength_signup(cls, v):
        """Validate password strength requirements for signup."""
        return validate_password_strength(v)


class UserLogin(BaseModel):
    """Schema for user login."""

    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(
        ..., min_length=1, max_length=128, description="User's password"
    )


class UserUpdate(BaseModel):
    """Schema for updating user information."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    chanting_rounds: Optional[int] = Field(None, ge=0, le=200)


class UserOut(UserBase):
    """Schema for user response (public information)."""

    id: int = Field(..., description="User's unique identifier")
    photo: Optional[str] = Field(None, description="User's profile photo path")
    created_at: Optional[datetime] = Field(
        None, description="Account creation timestamp"
    )
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    """Schema for JWT token response."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")


class TokenData(BaseModel):
    """Schema for token payload data."""

    email: Optional[str] = Field(None, description="User email from token")


# Health check schemas
class HealthResponse(BaseModel):
    """Schema for health check response."""

    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    version: str = Field(..., description="Application version")


class ErrorResponse(BaseModel):
    """Schema for error responses."""

    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(
        None, description="Error code for programmatic handling"
    )
