"""
Center schemas for API request/response validation.

Defines Pydantic models for ISKCON center data.
"""

from pydantic import BaseModel, Field


class CenterOut(BaseModel):
    """Schema for ISKCON center response."""

    id: int = Field(..., description="Center unique identifier")
    country: str = Field(..., description="Country name")
    state_province: str = Field(..., description="State or Province name")
    city: str = Field(..., description="City name")

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "country": "India",
                "state_province": "West Bengal",
                "city": "Mayapur",
            }
        }


class CenterListResponse(BaseModel):
    """Standardized response for center list operations."""

    success: bool = Field(
        ...,
        description="Indicates if the operation was successful",
        examples=[True],
    )
    status_code: int = Field(..., description="HTTP status code", examples=[200])
    message: str = Field(
        ...,
        description="Human-readable message explaining the result",
        examples=["Centers retrieved successfully"],
    )
    data: list[CenterOut] = Field(..., description="List of ISKCON centers")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "status_code": 200,
                "message": "Centers retrieved successfully",
                "data": [
                    {
                        "id": 1,
                        "country": "India",
                        "state_province": "West Bengal",
                        "city": "Mayapur",
                    },
                    {
                        "id": 2,
                        "country": "India",
                        "state_province": "Uttar Pradesh",
                        "city": "Vrindavan",
                    },
                ],
            }
        }
