"""
Authentication schemas.

This module contains Pydantic models for authentication-related requests and responses.
"""

from pydantic import BaseModel, Field


class Token(BaseModel):
    """Schema for JWT token response."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")


class TokenData(BaseModel):
    """Schema for token payload data."""

    email: str | None = Field(None, description="User email from token")
