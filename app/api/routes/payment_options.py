"""
API routes for payment option management.

This module provides CRUD endpoints for payment options (admin only).
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.db.models import Devotee
from app.db.session import get_db
from app.schemas.payment_option import (
    PaymentOptionCreate,
    PaymentOptionOut,
    PaymentOptionUpdate,
)
from app.services.payment_option_service import PaymentOptionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payment-options", tags=["Payment Options"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_payment_option(
    payment_data: PaymentOptionCreate,
    current_user: Devotee = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Create a new payment option (admin only)."""
    try:
        service = PaymentOptionService(db)
        payment_option = service.create_payment_option(payment_data)

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "success": True,
                "status_code": 201,
                "message": "Payment option created successfully",
                "data": PaymentOptionOut.model_validate(payment_option).model_dump(mode="json"),
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating payment option: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create payment option",
        )


@router.get("")
def list_payment_options(
    active_only: bool = True,
    db: Session = Depends(get_db),
):
    """List all payment options."""
    try:
        service = PaymentOptionService(db)
        payment_options = service.list_payment_options(active_only=active_only)

        # Build response manually
        options_out = []
        for option in payment_options:
            option_dict = {
                "id": option.id,
                "name": option.name,
                "payment_method": option.payment_method,
                "bank_account_number": option.bank_account_number,
                "ifsc_code": option.ifsc_code,
                "bank_name": option.bank_name,
                "branch_name": option.branch_name,
                "account_holder_name": option.account_holder_name,
                "account_type": option.account_type,
                "upi_id": option.upi_id,
                "upi_phone_number": option.upi_phone_number,
                "qr_code_path": option.qr_code_path,
                "is_active": option.is_active,
                "notes": option.notes,
                "created_at": option.created_at.isoformat() if option.created_at else None,
                "updated_at": option.updated_at.isoformat() if option.updated_at else None,
            }
            options_out.append(option_dict)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "status_code": 200,
                "message": "Payment options retrieved successfully",
                "data": options_out,
            },
        )
    except Exception as e:
        logger.error(f"Error listing payment options: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list payment options",
        )


@router.get("/{payment_option_id}")
def get_payment_option(
    payment_option_id: int,
    db: Session = Depends(get_db),
):
    """Get a specific payment option by ID."""
    try:
        service = PaymentOptionService(db)
        payment_option = service.get_payment_option(payment_option_id)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "status_code": 200,
                "message": "Payment option retrieved successfully",
                "data": PaymentOptionOut.model_validate(payment_option).model_dump(mode="json"),
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting payment option: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get payment option",
        )


@router.put("/{payment_option_id}")
def update_payment_option(
    payment_option_id: int,
    payment_data: PaymentOptionUpdate,
    current_user: Devotee = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update a payment option (admin only)."""
    try:
        service = PaymentOptionService(db)
        payment_option = service.update_payment_option(payment_option_id, payment_data)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "status_code": 200,
                "message": "Payment option updated successfully",
                "data": PaymentOptionOut.model_validate(payment_option).model_dump(mode="json"),
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating payment option: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update payment option",
        )


@router.delete("/{payment_option_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_payment_option(
    payment_option_id: int,
    current_user: Devotee = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete a payment option (admin only)."""
    try:
        service = PaymentOptionService(db)
        service.delete_payment_option(payment_option_id)
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting payment option: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete payment option",
        )
