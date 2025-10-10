"""
Authentication schemas.

This module contains Pydantic models for authentication-related requests and responses.
"""

from typing import Any

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Schema for login request."""

    email: EmailStr = Field(
        ...,
        description="User email address",
        examples=["radha.krishna@example.com"],
    )
    password: str = Field(
        ...,
        min_length=8,
        description="User password",
        examples=["SecurePass123!"],
    )

    class Config:
        json_schema_extra = {
            "example": {
                "email": "radha.krishna@example.com",
                "password": "SecurePass123!",
            }
        }


class LoginResponse(BaseModel):
    """Standardized schema for all login responses (success and error)."""

    success: bool = Field(
        ...,
        description="Indicates if the login was successful",
        examples=[True],
    )
    status_code: int = Field(..., description="HTTP status code", examples=[200])
    message: str = Field(
        ...,
        description="Human-readable message explaining the result",
        examples=["Login successful"],
    )
    data: dict[str, Any] | None = Field(
        None, description="Optional response data (omitted for errors)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "status_code": 200,
                "message": "Login successful",
                "data": {
                    "user_id": 123,
                    "email": "radha.krishna@example.com",
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer",
                    "expires_in": 3600,
                },
            }
        }
