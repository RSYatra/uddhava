"""
ISKCON Centers API endpoints.

Provides authenticated read-only access to ISKCON center data
with prefix-based search functionality.
"""

import logging

from fastapi import APIRouter, Depends, Query, status

from app.core.security import get_current_user
from app.data.centers import CENTERS
from app.db.models import Devotee
from app.schemas.center import CenterListResponse, CenterOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/centers", tags=["Master Database"])


@router.get(
    "/",
    response_model=CenterListResponse,
    summary="List ISKCON Centers",
    description="Get list of all ISKCON centers worldwide with optional prefix-based search",
)
async def get_centers(
    search: str | None = Query(
        None,
        max_length=100,
        description="Prefix search (case-insensitive) - filters by any field starting with search term",
    ),
    current_user: Devotee = Depends(get_current_user),
):
    """
    Retrieve list of ISKCON centers.

    Authentication required. Supports prefix-based search across all fields.

    Args:
        search: Optional search term for prefix filtering
        current_user: Authenticated user (injected by dependency)

    Returns:
        CenterListResponse with list of centers

    Example:
        - GET /api/v1/centers - Returns all 180 centers
        - GET /api/v1/centers?search=India - Returns centers where any field starts with "India"
        - GET /api/v1/centers?search=M - Returns centers where any field starts with "M"
    """
    logger.info(
        f"Fetching centers for user {current_user.email}"
        + (f" with search: {search}" if search else "")
    )

    # Start with all centers
    filtered_centers = CENTERS

    # Apply prefix-based search if provided
    if search:
        search_lower = search.lower()
        filtered_centers = [
            center
            for center in CENTERS
            if any(
                str(value).lower().startswith(search_lower)
                for value in center.values()
                if value is not None
            )
        ]

    # Convert to Pydantic models
    centers_out = [CenterOut(**center) for center in filtered_centers]

    logger.info(f"Returning {len(centers_out)} centers")

    return CenterListResponse(
        success=True,
        status_code=status.HTTP_200_OK,
        message=f"Centers retrieved successfully{f' (filtered by: {search})' if search else ''}",
        data=centers_out,
    )
