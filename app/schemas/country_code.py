"""
Country Code schemas for API request/response validation.

Defines Pydantic models for ISO country code data.
"""

from pydantic import BaseModel, Field


class CountryCodeOut(BaseModel):
    """Schema for country code response."""

    id: int = Field(..., description="Country unique identifier")
    country: str = Field(..., description="Country name")
    alpha2: str = Field(..., description="ISO 3166 Alpha-2 code")
    alpha3: str = Field(..., description="ISO 3166 Alpha-3 code")
    code: str = Field(..., description="International calling code")

    class Config:
        json_schema_extra = {
            "example": {
                "id": 97,
                "country": "India",
                "alpha2": "IN",
                "alpha3": "IND",
                "code": "91",
            }
        }


class CountryCodeListResponse(BaseModel):
    """Standardized response for country code list operations."""

    success: bool = Field(
        ...,
        description="Indicates if the operation was successful",
        examples=[True],
    )
    status_code: int = Field(..., description="HTTP status code", examples=[200])
    message: str = Field(
        ...,
        description="Human-readable message explaining the result",
        examples=["Country codes retrieved successfully"],
    )
    data: list[CountryCodeOut] = Field(..., description="List of country codes")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "status_code": 200,
                "message": "Country codes retrieved successfully",
                "data": [
                    {
                        "id": 97,
                        "country": "India",
                        "alpha2": "IN",
                        "alpha3": "IND",
                        "code": "91",
                    },
                    {
                        "id": 229,
                        "country": "United States",
                        "alpha2": "US",
                        "alpha3": "USA",
                        "code": "1",
                    },
                ],
            }
        }
