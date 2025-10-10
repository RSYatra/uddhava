"""
Standardized response schemas for devotee management endpoints.

All devotee endpoints follow the same response format as authentication endpoints:
{success, status_code, message, data}
"""

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.devotee import DevoteeListResponse, DevoteeOut, DevoteeStatsResponse


class StandardDevoteeResponse(BaseModel):
    """Standardized response for single devotee operations."""

    success: bool = Field(
        ...,
        description="Indicates if the operation was successful",
        examples=[True],
    )
    status_code: int = Field(..., description="HTTP status code", examples=[200])
    message: str = Field(
        ...,
        description="Human-readable message explaining the result",
        examples=["Devotee retrieved successfully"],
    )
    data: DevoteeOut | None = Field(None, description="Devotee data (null for errors)")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "status_code": 200,
                "message": "Devotee retrieved successfully",
                "data": {
                    "id": 123,
                    "legal_name": "Radha Krishna Das",
                    "email": "radha.krishna@example.com",
                    # ... other devotee fields
                },
            }
        }


class StandardDevoteeListResponse(BaseModel):
    """Standardized response for devotee list operations."""

    success: bool = Field(
        ...,
        description="Indicates if the operation was successful",
        examples=[True],
    )
    status_code: int = Field(..., description="HTTP status code", examples=[200])
    message: str = Field(
        ...,
        description="Human-readable message explaining the result",
        examples=["Devotees retrieved successfully"],
    )
    data: DevoteeListResponse | None = Field(
        None, description="List data with pagination (null for errors)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "status_code": 200,
                "message": "Devotees retrieved successfully",
                "data": {
                    "devotees": [],
                    "total": 100,
                    "page": 1,
                    "limit": 50,
                    "total_pages": 2,
                },
            }
        }


class StandardDevoteeStatsResponse(BaseModel):
    """Standardized response for devotee statistics."""

    success: bool = Field(
        ...,
        description="Indicates if the operation was successful",
        examples=[True],
    )
    status_code: int = Field(..., description="HTTP status code", examples=[200])
    message: str = Field(
        ...,
        description="Human-readable message explaining the result",
        examples=["Statistics retrieved successfully"],
    )
    data: DevoteeStatsResponse | None = Field(None, description="Statistics data (null for errors)")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "status_code": 200,
                "message": "Statistics retrieved successfully",
                "data": {
                    "total_devotees": 1000,
                    "by_gender": {},
                    "by_initiation_status": {},
                    # ... other stats
                },
            }
        }


class StandardSearchResponse(BaseModel):
    """Standardized response for search operations."""

    success: bool = Field(
        ...,
        description="Indicates if the operation was successful",
        examples=[True],
    )
    status_code: int = Field(..., description="HTTP status code", examples=[200])
    message: str = Field(
        ...,
        description="Human-readable message explaining the result",
        examples=["Search completed successfully"],
    )
    data: dict[str, Any] | None = Field(None, description="Search results (null for errors)")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "status_code": 200,
                "message": "Search completed successfully",
                "data": {
                    "results": [],
                    "count": 10,
                    "query": "search term",
                },
            }
        }


class StandardValidationResponse(BaseModel):
    """Standardized response for validation operations."""

    success: bool = Field(
        ...,
        description="Indicates if the operation was successful",
        examples=[True],
    )
    status_code: int = Field(..., description="HTTP status code", examples=[200])
    message: str = Field(
        ...,
        description="Human-readable message explaining the result",
        examples=["Validation completed successfully"],
    )
    data: dict[str, Any] | None = Field(None, description="Validation result (null for errors)")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "status_code": 200,
                "message": "Email is available",
                "data": {
                    "available": True,
                    "email": "test@example.com",
                },
            }
        }
