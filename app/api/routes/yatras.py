"""
API routes for yatra management.

This module provides REST API endpoints for yatra CRUD operations.
Admin-only endpoints for creating, updating, and deleting yatras.
Public endpoints for listing and viewing yatras.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.db.models import Devotee, PricingTemplateDetail, YatraStatus
from app.db.session import get_db
from app.schemas.payment_option import PaymentOptionOut
from app.schemas.pricing_template import PricingTemplateOut
from app.schemas.yatra import YatraCreate, YatraOut, YatraUpdate
from app.services.yatra_service import YatraService

router = APIRouter(prefix="/yatras", tags=["Yatras"])


@router.post(
    "",
    response_model=YatraOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create Yatra (Admin)",
    description="Create a new yatra. Admin access required.",
)
def create_yatra(
    yatra_data: YatraCreate,
    current_user: Devotee = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Create new yatra (admin only)."""
    try:
        service = YatraService(db)
        yatra = service.create_yatra(yatra_data, current_user.id)

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
    description="List all yatras with optional filters. Public endpoint.",
)
def list_yatras(
    status_filter: YatraStatus | None = Query(None, description="Filter by status"),
    upcoming_only: bool = Query(False, description="Show only upcoming yatras"),
    featured_only: bool = Query(False, description="Show only featured yatras"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
):
    """List yatras with filters and pagination."""
    service = YatraService(db)
    result = service.list_yatras(
        status_filter=status_filter,
        upcoming_only=upcoming_only,
        featured_only=featured_only,
        page=page,
        page_size=page_size,
    )

    yatras_out = [YatraOut.model_validate(y).model_dump(mode="json") for y in result["yatras"]]

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "status_code": status.HTTP_200_OK,
            "message": f"Found {len(yatras_out)} yatra(s)",
            "data": {
                "yatras": yatras_out,
                "page": result["page"],
                "page_size": result["page_size"],
                "has_more": result["has_more"],
            },
        },
    )


@router.get(
    "/{yatra_id}",
    summary="Get Yatra Details",
    description="Get detailed information about a specific yatra including pricing, payment options, and registration stats. Public endpoint.",
)
def get_yatra(
    yatra_id: int,
    include_stats: bool = Query(True, description="Include registration statistics"),
    db: Session = Depends(get_db),
):
    """Get yatra details with pricing, payment options, and optional statistics."""
    try:
        service = YatraService(db)
        result = service.get_yatra(yatra_id, include_stats=include_stats)

        yatra_data = YatraOut.model_validate(result["yatra"]).model_dump(mode="json")
        yatra_data["is_registration_open"] = result["is_registration_open"]

        if include_stats and "stats" in result:
            yatra_data["registration_stats"] = result["stats"]

        # Add pricing template details
        pricing_template = service.get_yatra_pricing_template(yatra_id)
        if pricing_template:
            # Load pricing details
            pricing_details = (
                db.query(PricingTemplateDetail)
                .filter(PricingTemplateDetail.template_id == pricing_template.id)
                .all()
            )
            pricing_template.pricing_details = pricing_details
            yatra_data["pricing_template"] = PricingTemplateOut.model_validate(
                pricing_template
            ).model_dump(mode="json")

        # Add payment options
        payment_options = service.get_yatra_payment_options(yatra_id)
        yatra_data["payment_options"] = [
            PaymentOptionOut.model_validate(p).model_dump(mode="json") for p in payment_options
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
    except ValidationError as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Yatra data validation failed: {str(e.errors()[0]['msg'])}",
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


@router.put(
    "/{yatra_id}",
    response_model=YatraOut,
    summary="Update Yatra (Admin)",
    description="Update yatra details. Admin access required.",
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
        yatra = service.update_yatra(yatra_id, yatra_data, current_user.id)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "status_code": status.HTTP_200_OK,
                "message": "Yatra updated successfully",
                "data": YatraOut.model_validate(yatra).model_dump(mode="json"),
            },
        )
    except ValidationError as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "success": False,
                "status_code": status.HTTP_400_BAD_REQUEST,
                "message": f"Invalid yatra data: {str(e.errors()[0]['msg'])}",
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
    "/{yatra_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Yatra (Admin)",
    description="Soft delete a yatra. Admin access required. Cannot delete yatras with confirmed registrations.",
)
def delete_yatra(
    yatra_id: int,
    current_user: Devotee = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete yatra (admin only)."""
    try:
        service = YatraService(db)
        service.delete_yatra(yatra_id, current_user.id)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "status_code": status.HTTP_200_OK,
                "message": "Yatra deleted successfully",
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
