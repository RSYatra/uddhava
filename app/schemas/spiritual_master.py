"""
Spiritual Master schemas for API request/response validation.

Defines Pydantic models for ISKCON spiritual master data.
"""

from pydantic import BaseModel, Field


class SpiritualMasterOut(BaseModel):
    """Schema for spiritual master response."""

    id: int = Field(..., description="Spiritual master unique identifier")
    name: str = Field(..., description="Full name of the spiritual master")
    initials: str | None = Field(None, description="Abbreviated initials")
    accepting_disciples: bool = Field(..., description="Whether currently accepting disciples")

    class Config:
        json_schema_extra = {
            "example": {
                "id": 114,
                "name": "HH Radhanath Swami",
                "initials": "RNS",
                "accepting_disciples": True,
            }
        }


class SpiritualMasterListResponse(BaseModel):
    """Standardized response for spiritual master list operations."""

    success: bool = Field(
        ...,
        description="Indicates if the operation was successful",
        examples=[True],
    )
    status_code: int = Field(..., description="HTTP status code", examples=[200])
    message: str = Field(
        ...,
        description="Human-readable message explaining the result",
        examples=["Spiritual masters retrieved successfully"],
    )
    data: list[SpiritualMasterOut] = Field(..., description="List of spiritual masters")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "status_code": 200,
                "message": "Spiritual masters retrieved successfully",
                "data": [
                    {
                        "id": 1,
                        "name": "HDG A.C. Bhaktivedanta Swami Prabhupada",
                        "initials": None,
                        "accepting_disciples": False,
                    },
                    {
                        "id": 114,
                        "name": "HH Radhanath Swami",
                        "initials": "RNS",
                        "accepting_disciples": True,
                    },
                ],
            }
        }
