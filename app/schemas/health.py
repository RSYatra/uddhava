"""
Health check schemas.

This module contains Pydantic models for health check responses.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Schema for health check response."""

    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    version: str = Field(..., description="Application version")


class ErrorResponse(BaseModel):
    """Schema for error responses."""

    detail: str = Field(..., description="Error message")
    error_code: str | None = Field(None, description="Error code for programmatic handling")
