"""
Email verification request and response schemas.

This module defines the Pydantic models for email verification endpoints,
including verification requests and responses.
"""

from typing import Any

from pydantic import BaseModel, EmailStr, Field


class EmailVerificationRequest(BaseModel):
    """Schema for email verification request."""

    token: str

    class Config:
        json_schema_extra = {
            "example": {
                "token": "abc123xyz789",
            }
        }


class EmailVerificationResponse(BaseModel):
    """Schema for email verification response."""

    message: str
    email: EmailStr
    verified: bool

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Email verified successfully!",
                "email": "user@example.com",
                "verified": True,
            }
        }


class ResendVerificationRequest(BaseModel):
    """Schema for resending verification email request."""

    email: EmailStr

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
            }
        }


class ResendVerificationResponse(BaseModel):
    """Schema for resending verification email response."""

    message: str
    email: EmailStr

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Verification email has been resent successfully!",
                "email": "user@example.com",
            }
        }


class SignupResponse(BaseModel):
    """Standardized schema for all signup responses (success and error)."""

    success: bool = Field(
        ...,
        description="Indicates if the request was successful",
        examples=[True],
    )
    status_code: int = Field(..., description="HTTP status code", examples=[200])
    message: str = Field(
        ...,
        description="Human-readable message explaining the result",
        examples=[
            "Registration successful. Verification email sent. Please check your inbox to verify your email address."
        ],
    )
    data: dict[str, Any] | None = Field(
        None, description="Optional response data (omitted for errors)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "status_code": 200,
                "message": "Registration successful. Verification email sent. Please check your inbox to verify your email address.",
                "data": {
                    "user_id": 123,
                    "email": "radha.krishna@example.com",
                    "email_verified": False,
                },
            }
        }
