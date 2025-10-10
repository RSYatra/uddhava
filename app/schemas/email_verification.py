"""
Email verification request and response schemas.

This module defines the Pydantic models for email verification endpoints,
including verification requests and responses.
"""

from typing import Any

from pydantic import BaseModel, EmailStr, Field


class EmailVerificationRequest(BaseModel):
    """Schema for email verification request."""

    token: str = Field(
        ...,
        min_length=32,
        max_length=256,
        description="Email verification token from the verification link",
        examples=["abc123xyz789def456ghi789jkl012mno345pqr678"],
    )

    class Config:
        json_schema_extra = {
            "example": {
                "token": "abc123xyz789def456ghi789jkl012mno345pqr678",
            }
        }


class EmailVerificationResponse(BaseModel):
    """Standardized schema for email verification responses (success and error)."""

    success: bool = Field(
        ...,
        description="Indicates if the verification was successful",
        examples=[True],
    )
    status_code: int = Field(..., description="HTTP status code", examples=[200])
    message: str = Field(
        ...,
        description="Human-readable message explaining the result",
        examples=["Email verified successfully. You can now login to your account."],
    )
    data: dict[str, Any] | None = Field(
        None, description="Optional response data (omitted for errors)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "status_code": 200,
                "message": "Email verified successfully. You can now login to your account.",
                "data": {
                    "email": "radha.krishna@example.com",
                    "email_verified": True,
                },
            }
        }


class ResendVerificationRequest(BaseModel):
    """Schema for resending verification email request."""

    email: EmailStr = Field(
        ...,
        description="Email address to resend verification to",
        examples=["radha.krishna@example.com"],
    )

    class Config:
        json_schema_extra = {
            "example": {
                "email": "radha.krishna@example.com",
            }
        }


class ResendVerificationResponse(BaseModel):
    """Standardized schema for resend verification responses (success and error)."""

    success: bool = Field(
        ...,
        description="Indicates if the request was successful",
        examples=[True],
    )
    status_code: int = Field(..., description="HTTP status code", examples=[200])
    message: str = Field(
        ...,
        description="Human-readable message explaining the result",
        examples=["Verification email sent. Please check your inbox and spam folder."],
    )
    data: dict[str, Any] | None = Field(
        None, description="Optional response data (omitted for errors)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "status_code": 200,
                "message": "Verification email sent. Please check your inbox and spam folder.",
                "data": {
                    "email": "radha.krishna@example.com",
                },
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
