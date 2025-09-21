"""
Pydantic schemas for password reset operations.

Provides request/response validation for forgot password and reset password endpoints.
"""

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.password_validation import validate_password_strength


class ForgotPasswordRequest(BaseModel):
    """Request schema for forgot password endpoint."""

    email: EmailStr = Field(..., description="Email address to send reset link to")

    class Config:
        json_schema_extra = {"example": {"email": "user@example.com"}}


class ForgotPasswordResponse(BaseModel):
    """Response schema for forgot password endpoint."""

    message: str = Field(..., description="Success message")
    email: str = Field(..., description="Email where reset link was sent")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Password reset link has been sent to your email",
                "email": "user@example.com",
            }
        }


class ResetPasswordRequest(BaseModel):
    """Request schema for reset password endpoint."""

    token: str = Field(..., description="Password reset token from email")
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password (minimum 8 characters)",
    )

    @field_validator("new_password")
    @classmethod
    def validate_new_password_strength(cls, v):
        """Validate password strength requirements."""
        return validate_password_strength(v)

    class Config:
        json_schema_extra = {
            "example": {
                "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                "new_password": "MyNewSecurePassword123!",
            }
        }


class ResetPasswordResponse(BaseModel):
    """Response schema for reset password endpoint."""

    message: str = Field(..., description="Success message")
    email: str = Field(..., description="Email of user whose password was reset")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Password has been reset successfully",
                "email": "user@example.com",
            }
        }
