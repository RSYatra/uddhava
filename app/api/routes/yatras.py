"""
API routes for yatra management.

This module provides REST API endpoints for yatra CRUD operations.
Admin-only endpoints for creating, updating, and deleting yatras.
Public endpoints for listing and viewing yatras.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.core.security import get_current_user
from app.db.models import Devotee
from app.db.session import get_db
from app.schemas.payment_option import PaymentOptionOut
from app.schemas.room_category import RoomCategoryOut
from app.schemas.yatra import YatraCreate, YatraOut, YatraUpdate
from app.services.yatra_service import YatraService

router = APIRouter(prefix="/yatras", tags=["Yatras"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create Yatra (Admin)",
    description="""
Create a new yatra.

**AUTHENTICATION:**
- Requires admin role

**NOTE:**
- Room categories and pricing are added separately via `/yatras/{id}/room-categories` endpoint
- Payment options are linked separately
    """,
)
def create_yatra(
    yatra_data: YatraCreate,
    current_user: Devotee = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Create new yatra (admin only)."""
    try:
        service = YatraService(db)
        yatra = service.create_yatra(yatra_data)

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "success": True,
                "status_code": status.HTTP_201_CREATED,
                "message": "Yatra created successfully",
                "data": YatraOut.model_validate(yatra).model_dump(mode="json"),
            },
        )
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={
                "success": False,
                "status_code": e.status_code,
                "message": e.detail,
                "data": None,
            },
        )


@router.get(
    "",
    summary="List Yatras",
    description="""
List all yatras with optional filters.

**QUERY PARAMETERS:**
- active_only (boolean, default: true): Show only active yatras
- page (integer, default: 0): Page offset for pagination
- limit (integer, default: 100, max: 100): Items per page

**RESPONSE:**
Returns list of yatras sorted by start date (newest first).

**AUTHENTICATION:**
- Requires authentication (any logged-in user)
    """,
)
def list_yatras(
    active_only: bool = Query(True, description="Show only active yatras"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=100, description="Maximum records to return"),
    current_user: Devotee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List yatras with filters and pagination."""
    try:
        service = YatraService(db)
        yatras = service.list_yatras(skip=skip, limit=limit, active_only=active_only)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "status_code": status.HTTP_200_OK,
                "message": "Yatras retrieved successfully",
                "data": {
                    "total": len(yatras),
                    "yatras": [YatraOut.model_validate(y).model_dump(mode="json") for y in yatras],
                },
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Failed to retrieve yatras: {str(e)}",
                "data": None,
            },
        )


@router.get(
    "/{yatra_id}",
    summary="Get Yatra Details",
    description="""
Get detailed information about a specific yatra including room categories and payment options.

**PATH PARAMETERS:**
- yatra_id (integer): ID of the yatra

**RESPONSE:**
Returns yatra details with:
- Basic yatra information
- List of available room categories with pricing
- List of available payment options

**AUTHENTICATION:**
- Requires authentication (any logged-in user)
    """,
)
def get_yatra(
    yatra_id: int,
    current_user: Devotee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get yatra details with room categories and payment options."""
    try:
        service = YatraService(db)
        result = service.get_yatra_with_details(yatra_id)

        yatra_data = YatraOut.model_validate(result["yatra"]).model_dump(mode="json")
        yatra_data["room_categories"] = [
            RoomCategoryOut.model_validate(rc).model_dump(mode="json")
            for rc in result["room_categories"]
        ]
        yatra_data["payment_options"] = [
            PaymentOptionOut.model_validate(po).model_dump(mode="json")
            for po in result["payment_options"]
        ]

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "status_code": status.HTTP_200_OK,
                "message": "Yatra retrieved successfully",
                "data": yatra_data,
            },
        )
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={
                "success": False,
                "status_code": e.status_code,
                "message": e.detail,
                "data": None,
            },
        )


@router.get(
    "/{yatra_id}/payment-options",
    summary="Get Payment Options with Aggregation",
    description="""
Get all payment options for a yatra with aggregated metadata.

**PATH PARAMETERS:**
- yatra_id (integer): ID of the yatra

**RESPONSE:**
Returns:
- Yatra ID and name
- Total number of payment options
- Aggregated summary by payment method (count of UPI, Bank Transfer, QR Code, etc.)
- Detailed list of all payment options

**AUTHENTICATION:**
- Requires authentication (any logged-in user)

**EXAMPLE RESPONSE:**
```json
{
  "success": true,
  "status_code": 200,
  "message": "Payment options retrieved successfully",
  "data": {
    "yatra_id": 1,
    "yatra_name": "Vrindavan Parikrama 2026",
    "total_options": 5,
    "summary": {
      "total": 5,
      "by_method": {
        "UPI": 2,
        "BANK_TRANSFER": 2,
        "QR_CODE": 1,
        "CASH": 0,
        "CHEQUE": 0
      }
    },
    "payment_options": [...]
  }
}
```
    """,
)
def get_payment_options_with_aggregation(
    yatra_id: int,
    current_user: Devotee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get payment options for a yatra with aggregated metadata."""
    try:
        service = YatraService(db)
        result = service.get_payment_options_with_aggregation(yatra_id)

        # Convert payment options to dict
        result["payment_options"] = [
            PaymentOptionOut.model_validate(po).model_dump(mode="json")
            for po in result["payment_options"]
        ]

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "status_code": status.HTTP_200_OK,
                "message": "Payment options retrieved successfully",
                "data": result,
            },
        )
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={
                "success": False,
                "status_code": e.status_code,
                "message": e.detail,
                "data": None,
            },
        )


@router.put(
    "/{yatra_id}",
    summary="Update Yatra (Admin)",
    description="""
Update yatra details.

**PATH PARAMETERS:**
- yatra_id (integer): ID of the yatra

**AUTHENTICATION:**
- Requires admin role

**NOTE:**
- Cannot update yatra that has already started
- All fields are optional
    """,
)
def update_yatra(
    yatra_id: int,
    yatra_data: YatraUpdate,
    current_user: Devotee = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update yatra (admin only)."""
    try:
        service = YatraService(db)
        yatra = service.update_yatra(yatra_id, yatra_data)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "status_code": status.HTTP_200_OK,
                "message": "Yatra updated successfully",
                "data": YatraOut.model_validate(yatra).model_dump(mode="json"),
            },
        )
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={
                "success": False,
                "status_code": e.status_code,
                "message": e.detail,
                "data": None,
            },
        )


@router.delete(
    "/{yatra_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Yatra (Admin)",
    description="""
Delete a yatra.

**PATH PARAMETERS:**
- yatra_id (integer): ID of the yatra

**AUTHENTICATION:**
- Requires admin role

**NOTE:**
- Cannot delete yatra with existing registrations
    """,
)
def delete_yatra(
    yatra_id: int,
    current_user: Devotee = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete yatra (admin only)."""
    try:
        service = YatraService(db)
        service.delete_yatra(yatra_id)

        return JSONResponse(
            status_code=status.HTTP_204_NO_CONTENT,
            content=None,
        )
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={
                "success": False,
                "status_code": e.status_code,
                "message": e.detail,
                "data": None,
            },
        )


@router.post(
    "/{yatra_id}/payment-options/{option_id}",
    summary="Add Payment Option to Yatra (Admin)",
    description="Associate a payment option with a yatra. Admin only.",
)
def add_payment_option_to_yatra(
    yatra_id: int,
    option_id: int,
    admin: Devotee = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Add payment option to yatra."""
    from app.services.payment_option_service import PaymentOptionService

    try:
        service = PaymentOptionService(db)
        service.add_payment_option_to_yatra(yatra_id, option_id)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "status_code": status.HTTP_200_OK,
                "message": "Payment option added to yatra successfully",
                "data": None,
            },
        )
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={
                "success": False,
                "status_code": e.status_code,
                "message": e.detail,
                "data": None,
            },
        )


@router.delete(
    "/{yatra_id}/payment-options/{option_id}",
    summary="Remove Payment Option from Yatra (Admin)",
    description="Remove payment option association from a yatra. Admin only.",
)
def remove_payment_option_from_yatra(
    yatra_id: int,
    option_id: int,
    admin: Devotee = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Remove payment option from yatra."""
    from app.services.payment_option_service import PaymentOptionService

    try:
        service = PaymentOptionService(db)
        service.remove_payment_option_from_yatra(yatra_id, option_id)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "status_code": status.HTTP_200_OK,
                "message": "Payment option removed from yatra successfully",
                "data": None,
            },
        )
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={
                "success": False,
                "status_code": e.status_code,
                "message": e.detail,
                "data": None,
            },
        )
