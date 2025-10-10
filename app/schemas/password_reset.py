"""
Pydantic schemas for password reset operations.

Provides request/response validation for forgot password and reset password endpoints.
"""

from typing import Any

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.password_validation import validate_password_strength


class ForgotPasswordRequest(BaseModel):
    """Request schema for forgot password endpoint."""

    email: EmailStr = Field(
        ...,
        description="Email address to send reset link to",
        examples=["radha.krishna@example.com"],
    )

    class Config:
        json_schema_extra = {"example": {"email": "radha.krishna@example.com"}}


class ForgotPasswordResponse(BaseModel):
    """Standardized schema for forgot password responses (success and error)."""

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
            "If this email is registered and verified, you will receive password reset instructions."
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
                "message": "If this email is registered and verified, you will receive password reset instructions.",
                "data": {
                    "email": "radha.krishna@example.com",
                },
            }
        }


class ResetPasswordRequest(BaseModel):
    """Request schema for reset password endpoint."""

    token: str = Field(
        ...,
        min_length=32,
        max_length=256,
        description="Password reset token from email",
        examples=["abc123xyz789def456ghi789jkl012mno345pqr678"],
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password (8-128 chars with uppercase, lowercase, digit, special character)",
        examples=["MyNewSecurePassword123!"],
    )

    @field_validator("new_password")
    @classmethod
    def validate_new_password_strength(cls, v):
        """Validate password strength requirements."""
        return validate_password_strength(v)

    class Config:
        json_schema_extra = {
            "example": {
                "token": "abc123xyz789def456ghi789jkl012mno345pqr678",
                "new_password": "MyNewSecurePassword123!",
            }
        }


class ResetPasswordResponse(BaseModel):
    """Standardized schema for reset password responses (success and error)."""

    success: bool = Field(
        ...,
        description="Indicates if the password reset was successful",
        examples=[True],
    )
    status_code: int = Field(..., description="HTTP status code", examples=[200])
    message: str = Field(
        ...,
        description="Human-readable message explaining the result",
        examples=["Password reset successful. You can now login with your new password."],
    )
    data: dict[str, Any] | None = Field(
        None, description="Optional response data (omitted for errors)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "status_code": 200,
                "message": "Password reset successful. You can now login with your new password.",
                "data": {
                    "email": "radha.krishna@example.com",
                },
            }
        }


class AdminResetPasswordRequest(BaseModel):
    """Request schema for admin password reset endpoint."""

    devotee_id: int = Field(
        ...,
        gt=0,
        description="ID of the devotee whose password to reset",
        examples=[123],
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password (8-128 chars with uppercase, lowercase, digit, special character)",
        examples=["AdminResetPass123!"],
    )

    @field_validator("new_password")
    @classmethod
    def validate_new_password_strength(cls, v):
        """Validate password strength requirements."""
        return validate_password_strength(v)

    class Config:
        json_schema_extra = {
            "example": {
                "devotee_id": 123,
                "new_password": "AdminResetPass123!",
            }
        }


class AdminResetPasswordResponse(BaseModel):
    """Standardized schema for admin password reset responses (success and error)."""

    success: bool = Field(
        ...,
        description="Indicates if the password reset was successful",
        examples=[True],
    )
    status_code: int = Field(..., description="HTTP status code", examples=[200])
    message: str = Field(
        ...,
        description="Human-readable message explaining the result",
        examples=["Password reset successful by admin"],
    )
    data: dict[str, Any] | None = Field(
        None, description="Optional response data (omitted for errors)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "status_code": 200,
                "message": "Password reset successful by admin",
                "data": {
                    "devotee_id": 123,
                    "admin_id": 1,
                },
            }
        }
