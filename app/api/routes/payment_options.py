"""
Payment option API endpoints.

This module provides CRUD endpoints for managing reusable payment options
that can be associated with multiple yatras.
"""

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_admin
from app.db.models import Devotee
from app.db.session import get_db
from app.schemas.payment_option import (
    PaymentOptionCreate,
    PaymentOptionOut,
    PaymentOptionUpdate,
)
from app.services.payment_option_service import PaymentOptionService

router = APIRouter(prefix="/payment-options", tags=["Payment Options"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create Payment Option (Admin)",
    description="""
Create a new reusable payment option that can be associated with multiple yatras.

**REQUIRED FIELDS:**
- name (string): Display name for the payment option
- method (string): Payment method - "UPI", "BANK_TRANSFER", "QR_CODE", "CASH", or "CHEQUE"
- instructions (string): Payment instructions for users

**CONDITIONAL REQUIRED FIELDS (based on method):**

For **UPI**:
- upi_id (string, required): UPI ID (e.g., "yatra@upi")

For **BANK_TRANSFER**:
- account_holder (string, required): Account holder name
- account_number (string, required): Bank account number
- ifsc_code (string, required): IFSC code
- bank_name (string, required): Bank name
- branch (string, optional): Branch name

For **QR_CODE**:
- qr_code_url (string, required): URL to QR code image

For **CASH** or **CHEQUE**:
- No additional fields required

**OPTIONAL FIELDS:**
- is_active (boolean): Whether the option is active (default: true)

**AUTHENTICATION:** Admin only
""",
)
def create_payment_option(
    option_data: PaymentOptionCreate,
    admin: Devotee = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Create new payment option. Admin only."""
    service = PaymentOptionService(db)
    payment_option = service.create_payment_option(option_data)

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "success": True,
            "status_code": status.HTTP_201_CREATED,
            "message": "Payment option created successfully",
            "data": PaymentOptionOut.model_validate(payment_option).model_dump(mode="json"),
        },
    )


@router.get(
    "",
    summary="List Payment Options",
    description="Get all payment options. Optionally filter by active status. Requires authentication.",
)
def list_payment_options(
    active_only: bool = False,
    current_user: Devotee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all payment options. Requires authentication."""
    service = PaymentOptionService(db)
    payment_options = service.list_payment_options(active_only=active_only)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "status_code": status.HTTP_200_OK,
            "message": "Payment options retrieved successfully",
            "data": [
                PaymentOptionOut.model_validate(po).model_dump(mode="json")
                for po in payment_options
            ],
        },
    )


@router.get(
    "/{option_id}",
    summary="Get Payment Option",
    description="Get payment option details by ID. Requires authentication.",
)
def get_payment_option(
    option_id: int,
    current_user: Devotee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get payment option by ID. Requires authentication."""
    service = PaymentOptionService(db)
    payment_option = service.get_payment_option(option_id)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "status_code": status.HTTP_200_OK,
            "message": "Payment option retrieved successfully",
            "data": PaymentOptionOut.model_validate(payment_option).model_dump(mode="json"),
        },
    )


@router.put(
    "/{option_id}",
    summary="Update Payment Option (Admin)",
    description="""
Update an existing payment option.

**ALL FIELDS OPTIONAL:**
- name (string): Updated display name
- method (string): Updated payment method
- instructions (string): Updated instructions
- upi_id (string): Updated UPI ID (for UPI method)
- account_holder (string): Updated account holder (for BANK_TRANSFER)
- account_number (string): Updated account number (for BANK_TRANSFER)
- ifsc_code (string): Updated IFSC code (for BANK_TRANSFER)
- bank_name (string): Updated bank name (for BANK_TRANSFER)
- branch (string): Updated branch (for BANK_TRANSFER)
- qr_code_url (string): Updated QR code URL (for QR_CODE)
- is_active (boolean): Updated active status

**NOTE:** Only provide fields you want to update.

**AUTHENTICATION:** Admin only
""",
)
def update_payment_option(
    option_id: int,
    update_data: PaymentOptionUpdate,
    admin: Devotee = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update payment option. Admin only."""
    service = PaymentOptionService(db)
    payment_option = service.update_payment_option(option_id, update_data)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "status_code": status.HTTP_200_OK,
            "message": "Payment option updated successfully",
            "data": PaymentOptionOut.model_validate(payment_option).model_dump(mode="json"),
        },
    )


@router.delete(
    "/{option_id}",
    summary="Delete Payment Option (Admin)",
    description="Delete a payment option. Admin only.",
)
def delete_payment_option(
    option_id: int,
    admin: Devotee = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete payment option."""
    service = PaymentOptionService(db)
    service.delete_payment_option(option_id)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "status_code": status.HTTP_200_OK,
            "message": "Payment option deleted successfully",
            "data": None,
        },
    )
