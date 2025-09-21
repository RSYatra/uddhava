"""
Email verification request and response schemas.

This module defines the Pydantic models for email verification endpoints,
including verification requests and responses.
"""

from pydantic import BaseModel, EmailStr


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
    """Schema for signup response with email verification required."""

    message: str
    email: EmailStr
    verification_required: bool = True

    class Config:
        json_schema_extra = {
            "example": {
                "message": (
                    "Account created successfully! "
                    "Please check your email for verification link."
                ),
                "email": "user@example.com",
                "verification_required": True,
            }
        }
