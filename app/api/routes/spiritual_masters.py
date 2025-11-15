"""
Spiritual Masters API endpoints.

Provides authenticated read-only access to ISKCON spiritual master data
with prefix-based search functionality.
"""

import logging

from fastapi import APIRouter, Depends, Query, status

from app.core.security import get_current_user
from app.data.spiritual_masters import SPIRITUAL_MASTERS
from app.db.models import Devotee
from app.schemas.spiritual_master import SpiritualMasterListResponse, SpiritualMasterOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/spiritual-masters", tags=["Spiritual Masters"])


@router.get(
    "/",
    response_model=SpiritualMasterListResponse,
    summary="List Spiritual Masters",
    description="Get list of all ISKCON spiritual masters (both accepting and not accepting disciples) with optional prefix-based search",
)
async def get_spiritual_masters(
    search: str | None = Query(
        None,
        max_length=100,
        description="Prefix search (case-insensitive) - filters by any field starting with search term",
    ),
    current_user: Devotee = Depends(get_current_user),
):
    """
    Retrieve list of ISKCON spiritual masters.

    Authentication required. Returns all spiritual masters regardless of whether
    they are currently accepting disciples. Supports prefix-based search across all fields.

    Args:
        search: Optional search term for prefix filtering
        current_user: Authenticated user (injected by dependency)

    Returns:
        SpiritualMasterListResponse with list of spiritual masters

    Example:
        - GET /api/v1/spiritual-masters - Returns all 127 spiritual masters
        - GET /api/v1/spiritual-masters?search=HH Radh - Returns masters where any field starts with "HH Radh"
        - GET /api/v1/spiritual-masters?search=RNS - Returns masters where any field starts with "RNS"
        - GET /api/v1/spiritual-masters?search=B - Returns masters where any field starts with "B"
    """
    logger.info(
        f"Fetching spiritual masters for user {current_user.email}"
        + (f" with search: {search}" if search else "")
    )

    # Start with all spiritual masters (both accepting and not accepting disciples)
    filtered_masters = SPIRITUAL_MASTERS

    # Apply prefix-based search if provided
    if search:
        search_lower = search.lower()
        filtered_masters = [
            master
            for master in SPIRITUAL_MASTERS
            if any(
                str(value).lower().startswith(search_lower)
                for value in master.values()
                if value is not None
            )
        ]

    # Convert to Pydantic models
    masters_out = [SpiritualMasterOut(**master) for master in filtered_masters]

    logger.info(f"Returning {len(masters_out)} spiritual masters")

    return SpiritualMasterListResponse(
        success=True,
        status_code=status.HTTP_200_OK,
        message=f"Spiritual masters retrieved successfully{f' (filtered by: {search})' if search else ''}",
        data=masters_out,
    )
