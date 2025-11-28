"""
Room category API endpoints for yatra pricing management.

This module provides CRUD endpoints for managing room categories,
which are custom pricing categories created per yatra by admins.
"""

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.core.security import get_current_user
from app.db.models import Devotee
from app.db.session import get_db
from app.schemas.room_category import (
    RoomCategoryCreate,
    RoomCategoryOut,
    RoomCategoryUpdate,
)
from app.services.room_category_service import RoomCategoryService

router = APIRouter(prefix="/yatras/{yatra_id}/room-categories", tags=["Room Categories"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create Room Category (Admin)",
    description="""
Create a new room category for a yatra.

**REQUIRED FIELDS:**
- name (string, max 100 chars): Room category name (e.g., "Deluxe AC Suite", "Economy Shared")
  - Must be unique per yatra
  - Free-text, admin can enter any name
  - Examples: "Deluxe AC Suite", "Economy Shared", "VIP Room", "Budget Non-AC"
- price_per_person (decimal, > 0): Price per person in rupees
  - Must be greater than 0
  - Examples: 5000, 8000, 12000

**OPTIONAL FIELDS:**
- description (string, max 500 chars): Description of the room category
  - Examples: "Spacious AC room with attached bathroom and balcony"

**VALIDATION RULES:**
- Category name must be unique within the yatra
- Price must be positive

**AUTHENTICATION:**
- Requires admin role

**RESPONSE:**
Returns the created room category with ID, timestamps, and all details.
    """,
    responses={
        201: {
            "description": "Room category created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "status_code": 201,
                        "message": "Room category created successfully",
                        "data": {
                            "id": 1,
                            "yatra_id": 1,
                            "name": "Deluxe AC Suite",
                            "price_per_person": 12000,
                            "description": "Spacious AC room with attached bathroom",
                            "is_active": True,
                            "created_at": "2025-11-28T10:00:00Z",
                            "updated_at": "2025-11-28T10:00:00Z",
                        },
                    }
                }
            },
        },
        400: {
            "description": "Bad Request - Category name already exists",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "status_code": 400,
                        "message": "Room category 'Deluxe AC Suite' already exists for this yatra",
                        "data": None,
                    }
                }
            },
        },
        401: {"description": "Not authenticated"},
        403: {"description": "Forbidden - Admin role required"},
    },
)
async def create_room_category(
    yatra_id: int,
    category_data: RoomCategoryCreate,
    db: Session = Depends(get_db),
    admin: Devotee = Depends(require_admin),
):
    """Create a new room category for a yatra."""
    service = RoomCategoryService(db)
    category = service.create_room_category(yatra_id, category_data)

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "success": True,
            "status_code": status.HTTP_201_CREATED,
            "message": "Room category created successfully",
            "data": RoomCategoryOut.model_validate(category).model_dump(mode="json"),
        },
    )


@router.get(
    "",
    summary="List Room Categories",
    description="""
Get all room categories for a yatra.

**QUERY PARAMETERS:**
- include_inactive (boolean, default: false): Include inactive categories in the list

**RESPONSE:**
Returns list of room categories sorted by price (lowest to highest).

**AUTHENTICATION:**
- Requires authentication (any logged-in user)
    """,
    responses={
        200: {
            "description": "Room categories retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "status_code": 200,
                        "message": "Room categories retrieved successfully",
                        "data": {
                            "yatra_id": 1,
                            "total_categories": 3,
                            "categories": [
                                {
                                    "id": 1,
                                    "yatra_id": 1,
                                    "name": "Economy Shared",
                                    "price_per_person": 5000,
                                    "description": "Shared room with 4-6 devotees",
                                    "is_active": True,
                                    "created_at": "2025-11-28T10:00:00Z",
                                    "updated_at": "2025-11-28T10:00:00Z",
                                },
                                {
                                    "id": 2,
                                    "yatra_id": 1,
                                    "name": "Deluxe AC Suite",
                                    "price_per_person": 12000,
                                    "description": "Spacious AC room",
                                    "is_active": True,
                                    "created_at": "2025-11-28T10:00:00Z",
                                    "updated_at": "2025-11-28T10:00:00Z",
                                },
                            ],
                        },
                    }
                }
            },
        },
    },
)
async def list_room_categories(
    yatra_id: int,
    include_inactive: bool = False,
    current_user: Devotee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all room categories for a yatra."""
    service = RoomCategoryService(db)
    categories = service.get_room_categories_for_yatra(yatra_id, include_inactive)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "status_code": status.HTTP_200_OK,
            "message": "Room categories retrieved successfully",
            "data": {
                "yatra_id": yatra_id,
                "total_categories": len(categories),
                "categories": [
                    RoomCategoryOut.model_validate(cat).model_dump(mode="json")
                    for cat in categories
                ],
            },
        },
    )


@router.get(
    "/{category_id}",
    summary="Get Room Category",
    description="""
Get a specific room category by ID.

**PATH PARAMETERS:**
- category_id (integer): ID of the room category

**RESPONSE:**
Returns the room category details.

**AUTHENTICATION:**
- Requires authentication (any logged-in user)
    """,
    responses={
        200: {
            "description": "Room category retrieved successfully",
        },
        404: {
            "description": "Room category not found",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "status_code": 404,
                        "message": "Room category not found",
                        "data": None,
                    }
                }
            },
        },
    },
)
async def get_room_category(
    yatra_id: int,
    category_id: int,
    current_user: Devotee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific room category."""
    service = RoomCategoryService(db)
    category = service.get_room_category(category_id)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "status_code": status.HTTP_200_OK,
            "message": "Room category retrieved successfully",
            "data": RoomCategoryOut.model_validate(category).model_dump(mode="json"),
        },
    )


@router.put(
    "/{category_id}",
    summary="Update Room Category (Admin)",
    description="""
Update an existing room category.

**PATH PARAMETERS:**
- category_id (integer): ID of the room category

**OPTIONAL FIELDS:**
- name (string, max 100 chars): Updated category name
- price_per_person (decimal, > 0): Updated price per person
- description (string, max 500 chars): Updated description
- is_active (boolean): Whether the category is active

**VALIDATION RULES:**
- If updating name, it must not conflict with existing category names for this yatra
- If updating price, it must be positive

**AUTHENTICATION:**
- Requires admin role

**RESPONSE:**
Returns the updated room category.
    """,
    responses={
        200: {
            "description": "Room category updated successfully",
        },
        400: {
            "description": "Bad Request - Name conflict or invalid data",
        },
        401: {"description": "Not authenticated"},
        403: {"description": "Forbidden - Admin role required"},
        404: {"description": "Room category not found"},
    },
)
async def update_room_category(
    yatra_id: int,
    category_id: int,
    category_data: RoomCategoryUpdate,
    db: Session = Depends(get_db),
    admin: Devotee = Depends(require_admin),
):
    """Update a room category."""
    service = RoomCategoryService(db)
    category = service.update_room_category(category_id, category_data)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "status_code": status.HTTP_200_OK,
            "message": "Room category updated successfully",
            "data": RoomCategoryOut.model_validate(category).model_dump(mode="json"),
        },
    )


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Room Category (Admin)",
    description="""
Delete a room category.

**PATH PARAMETERS:**
- category_id (integer): ID of the room category

**AUTHENTICATION:**
- Requires admin role

**RESPONSE:**
Returns 204 No Content on successful deletion.

**NOTE:**
- Cannot delete category if it's used in active registrations (enforced by database constraints)
    """,
    responses={
        204: {"description": "Room category deleted successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "Forbidden - Admin role required"},
        404: {"description": "Room category not found"},
    },
)
async def delete_room_category(
    yatra_id: int,
    category_id: int,
    db: Session = Depends(get_db),
    admin: Devotee = Depends(require_admin),
):
    """Delete a room category."""
    service = RoomCategoryService(db)
    service.delete_room_category(category_id)

    return JSONResponse(
        status_code=status.HTTP_204_NO_CONTENT,
        content=None,
    )
