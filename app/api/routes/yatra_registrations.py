"""
API routes for yatra registration management.

This module provides REST API endpoints for registration operations including
creating, updating, payment upload, and status management.
"""

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.core.security import get_current_user
from app.db.models import Devotee, RegistrationStatus, UserRole
from app.db.session import get_db
from app.schemas.yatra_registration import (
    RegistrationCreate,
    RegistrationOut,
    RegistrationUpdate,
    StatusUpdateRequest,
)
from app.services.yatra_registration_service import YatraRegistrationService

router = APIRouter(prefix="/registrations", tags=["Yatra Registrations"])


@router.post(
    "",
    response_model=RegistrationOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create Registration",
    description="Create a new yatra registration. Authenticated users only.",
)
def create_registration(
    reg_data: RegistrationCreate,
    current_user: Devotee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create new yatra registration."""
    service = YatraRegistrationService(db)
    registration = service.create_registration(current_user.id, reg_data)

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "success": True,
            "status_code": status.HTTP_201_CREATED,
            "message": f"Registration created successfully. Registration number: {registration.registration_number}",
            "data": RegistrationOut.model_validate(registration).model_dump(mode="json"),
        },
    )


@router.get(
    "/my-registrations",
    summary="My Registrations",
    description="Get all registrations for the current user.",
)
def get_my_registrations(
    status_filter: RegistrationStatus | None = Query(None, description="Filter by status"),
    current_user: Devotee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all registrations for current user."""
    service = YatraRegistrationService(db)
    registrations = service.list_devotee_registrations(current_user.id, status_filter)

    regs_out = [RegistrationOut.model_validate(r).model_dump(mode="json") for r in registrations]

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "status_code": status.HTTP_200_OK,
            "message": f"Found {len(regs_out)} registration(s)",
            "data": regs_out,
        },
    )


@router.get(
    "/{reg_id}",
    response_model=RegistrationOut,
    summary="Get Registration Details",
    description="Get detailed information about a specific registration.",
)
def get_registration(
    reg_id: int,
    current_user: Devotee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get registration details."""
    service = YatraRegistrationService(db)
    is_admin = current_user.role == UserRole.ADMIN
    registration = service.get_registration(reg_id, current_user.id, is_admin)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "status_code": status.HTTP_200_OK,
            "message": "Registration retrieved successfully",
            "data": RegistrationOut.model_validate(registration).model_dump(mode="json"),
        },
    )


@router.put(
    "/{reg_id}",
    response_model=RegistrationOut,
    summary="Update Registration",
    description="Update registration details. Only allowed in PENDING status.",
)
def update_registration(
    reg_id: int,
    update_data: RegistrationUpdate,
    current_user: Devotee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update registration details."""
    service = YatraRegistrationService(db)
    registration = service.update_registration(reg_id, current_user.id, update_data)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "status_code": status.HTTP_200_OK,
            "message": "Registration updated successfully",
            "data": RegistrationOut.model_validate(registration).model_dump(mode="json"),
        },
    )


@router.post(
    "/{reg_id}/payment",
    response_model=RegistrationOut,
    summary="Upload Payment Screenshot",
    description="Upload payment screenshot and transition registration to PAYMENT_SUBMITTED status.",
)
async def upload_payment(
    reg_id: int,
    payment_screenshot: UploadFile = File(..., description="Payment screenshot (max 5MB)"),
    payment_reference: str | None = Form(None, description="Payment reference number"),
    current_user: Devotee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload payment screenshot."""
    service = YatraRegistrationService(db)
    registration = await service.upload_payment_screenshot(
        reg_id, current_user.id, payment_screenshot, payment_reference
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "status_code": status.HTTP_200_OK,
            "message": "Payment screenshot uploaded successfully. Awaiting admin verification.",
            "data": RegistrationOut.model_validate(registration).model_dump(mode="json"),
        },
    )


@router.post(
    "/{reg_id}/cancel",
    response_model=RegistrationOut,
    summary="Cancel Registration",
    description="Cancel your registration. Only allowed for PENDING or PAYMENT_SUBMITTED status.",
)
def cancel_registration(
    reg_id: int,
    cancellation_reason: str | None = Query(None, description="Reason for cancellation"),
    current_user: Devotee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel registration."""
    service = YatraRegistrationService(db)
    registration = service.cancel_registration(reg_id, current_user.id, cancellation_reason)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "status_code": status.HTTP_200_OK,
            "message": "Registration cancelled successfully",
            "data": RegistrationOut.model_validate(registration).model_dump(mode="json"),
        },
    )


@router.get(
    "/yatra/{yatra_id}",
    summary="List Yatra Registrations (Admin)",
    description="Get all registrations for a specific yatra. Admin access required.",
)
def list_yatra_registrations(
    yatra_id: int,
    status_filter: RegistrationStatus | None = Query(None, description="Filter by status"),
    current_user: Devotee = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all registrations for a yatra (admin only)."""
    service = YatraRegistrationService(db)
    registrations = service.list_yatra_registrations(yatra_id, status_filter)

    regs_out = [RegistrationOut.model_validate(r).model_dump(mode="json") for r in registrations]

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "status_code": status.HTTP_200_OK,
            "message": f"Found {len(regs_out)} registration(s) for yatra {yatra_id}",
            "data": regs_out,
        },
    )


@router.put(
    "/{reg_id}/status",
    response_model=RegistrationOut,
    summary="Update Registration Status (Admin)",
    description="Update registration status. Admin access required. Validates status transitions.",
)
def update_registration_status(
    reg_id: int,
    status_update: StatusUpdateRequest,
    current_user: Devotee = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update registration status (admin only)."""
    service = YatraRegistrationService(db)

    # Get current registration to pass current_status to validator
    registration = service.get_registration(reg_id, current_user.id, is_admin=True)

    registration = service.update_registration_status(
        reg_id=reg_id,
        new_status=status_update.status,
        admin_id=current_user.id,
        admin_remarks=status_update.admin_remarks,
        current_status=registration.status,
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "status_code": status.HTTP_200_OK,
            "message": f"Registration status updated to {status_update.status.value}",
            "data": RegistrationOut.model_validate(registration).model_dump(mode="json"),
        },
    )
