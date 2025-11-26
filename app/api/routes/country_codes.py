"""
Country Codes API endpoints.

Provides authenticated read-only access to ISO country code data
with prefix-based search functionality.
"""

import logging

from fastapi import APIRouter, Depends, Query, status

from app.core.security import get_current_user
from app.data.country_codes import COUNTRY_CODES
from app.db.models import Devotee
from app.schemas.country_code import CountryCodeListResponse, CountryCodeOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/country-codes", tags=["Master Database"])


@router.get(
    "/",
    response_model=CountryCodeListResponse,
    summary="List Country Codes",
    description="Get list of all ISO 3166 country codes with optional prefix-based search",
)
async def get_country_codes(
    search: str | None = Query(
        None,
        max_length=100,
        description="Prefix search (case-insensitive) - filters by any field starting with search term",
    ),
    current_user: Devotee = Depends(get_current_user),
):
    """
    Retrieve list of ISO 3166 country codes.

    Authentication required. Supports prefix-based search across all fields.

    Args:
        search: Optional search term for prefix filtering
        current_user: Authenticated user (injected by dependency)

    Returns:
        CountryCodeListResponse with list of country codes

    Example:
        - GET /api/v1/country-codes - Returns all 240 countries
        - GET /api/v1/country-codes?search=India - Returns countries where any field starts with "India"
        - GET /api/v1/country-codes?search=IN - Returns countries where any field starts with "IN"
        - GET /api/v1/country-codes?search=91 - Returns countries with code starting with "91"
    """
    logger.info(
        f"Fetching country codes for user {current_user.email}"
        + (f" with search: {search}" if search else "")
    )

    # Start with all country codes
    filtered_codes = COUNTRY_CODES

    # Apply prefix-based search if provided
    if search:
        search_lower = search.lower()
        filtered_codes = [
            code
            for code in COUNTRY_CODES
            if any(
                str(value).lower().startswith(search_lower)
                for value in code.values()
                if value is not None
            )
        ]

    # Convert to Pydantic models
    codes_out = [CountryCodeOut(**code) for code in filtered_codes]

    logger.info(f"Returning {len(codes_out)} country codes")

    return CountryCodeListResponse(
        success=True,
        status_code=status.HTTP_200_OK,
        message=f"Country codes retrieved successfully{f' (filtered by: {search})' if search else ''}",
        data=codes_out,
    )
