"""
API routes for yatra registration management.

This module provides REST API endpoints for group registrations with
individual member tracking.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.models import Devotee
from app.db.session import get_db
from app.schemas.payment_option import PaymentOptionOut
from app.schemas.yatra_member import YatraMemberOut
from app.schemas.yatra_registration import (
    PaymentStatusUpdate,
    RegistrationCreate,
    RegistrationOut,
)
from app.services.yatra_registration_service import YatraRegistrationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/yatra-registrations", tags=["Yatra Registrations"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create Group Registration",
    description="""
Create a new group registration with multiple members for a yatra.

**REQUIRED FIELDS:**
- yatra_id (integer): ID of the yatra to register for
- payment_option_id (integer): ID of the payment option to use
- members (array): List of member objects (at least 1 required)

**MEMBER OBJECT FIELDS:**
- legal_name (string, required): Full legal name
- date_of_birth (date, required): DOB in YYYY-MM-DD format (for age calculation)
- gender (string, required): "M" or "F"
- room_category (string, required): Room category name (must match available categories)
- room_preference (string, required): "MALE_SHARING", "FEMALE_SHARING", "FAMILY", or "FAMILY_WITH_CHILDREN"
- is_primary_registrant (boolean, required): Exactly one member must be true
- devotee_id (integer, optional): Link to registered devotee (required for primary registrant)
- mobile_number (string, optional): Contact number
- email (string, optional): Email address
- arrival_datetime (datetime, optional): Arrival date and time
- departure_datetime (datetime, optional): Departure date and time
- dietary_requirements (string, optional): Special dietary needs
- medical_conditions (string, optional): Medical conditions to be aware of

**PRICING:**
- Children under 5 years (at yatra start date): FREE
- Everyone 5 and above: Price per room category
- Total amount calculated automatically

**RESPONSE:**
- group_id: Human-readable format (e.g., "GRP-2026-1-001")
- registration: Registration details
- members: List of all members with calculated prices
- total_amount: Total amount for the group
- payment_options: Available payment methods

**AUTHENTICATION:** Required (any logged-in user)
""",
)
def create_registration(
    reg_data: RegistrationCreate,
    current_user: Devotee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create new group registration with members."""
    try:
        service = YatraRegistrationService(db)
        result = service.create_registration(current_user.id, reg_data)

        # Format response
        registration_out = RegistrationOut.model_validate(result["registration"]).model_dump(
            mode="json"
        )
        members_out = [
            YatraMemberOut.model_validate(m).model_dump(mode="json") for m in result["members"]
        ]
        payment_options_out = [
            PaymentOptionOut.model_validate(p).model_dump(mode="json")
            for p in result["payment_options"]
        ]

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "success": True,
                "status_code": status.HTTP_201_CREATED,
                "message": "Registration created successfully",
                "data": {
                    "group_id": result["group_id"],
                    "registration": registration_out,
                    "members": members_out,
                    "total_amount": result["total_amount"],
                    "payment_options": payment_options_out,
                },
            },
        )
    except ValidationError as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "success": False,
                "status_code": status.HTTP_400_BAD_REQUEST,
                "message": f"Invalid registration data: {str(e.errors()[0]['msg'])}",
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
    except Exception as e:
        logger.error(f"Unexpected error creating registration: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Failed to create registration",
                "data": None,
            },
        )


@router.get(
    "/{registration_id}",
    summary="Get Registration Details",
    description="Get registration details with member information. Authenticated users only.",
)
def get_registration(
    registration_id: int,
    current_user: Devotee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get registration with member details."""
    try:
        service = YatraRegistrationService(db)
        result = service.get_registration_by_id(registration_id, current_user.id)

        registration_out = RegistrationOut.model_validate(result["registration"]).model_dump(
            mode="json"
        )
        members_out = [
            YatraMemberOut.model_validate(m).model_dump(mode="json") for m in result["members"]
        ]

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "status_code": status.HTTP_200_OK,
                "message": "Registration retrieved successfully",
                "data": {
                    "registration": registration_out,
                    "members": members_out,
                },
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
    except Exception as e:
        logger.error(f"Unexpected error getting registration: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Failed to get registration",
                "data": None,
            },
        )


@router.get(
    "/group/{group_id}",
    summary="Get Group Registrations",
    description="Get all registrations and members for a group. Authenticated users only.",
)
def get_group_registrations(
    group_id: str,
    current_user: Devotee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all registrations for a group."""
    try:
        service = YatraRegistrationService(db)
        result = service.get_group_registrations(group_id, current_user.id)

        registrations_out = [
            RegistrationOut.model_validate(r).model_dump(mode="json")
            for r in result["registrations"]
        ]
        members_out = [
            YatraMemberOut.model_validate(m).model_dump(mode="json") for m in result["members"]
        ]

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "status_code": status.HTTP_200_OK,
                "message": "Group registrations retrieved successfully",
                "data": {
                    "group_id": result["group_id"],
                    "registrations": registrations_out,
                    "members": members_out,
                    "total_amount": int(result["total_amount"]),
                },
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
    except Exception as e:
        logger.error(f"Unexpected error getting group registrations: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Failed to get group registrations",
                "data": None,
            },
        )


@router.put(
    "/{registration_id}/payment-status",
    summary="Update Payment Status (Admin)",
    description="""
Admin endpoint to approve or reject payment after reviewing screenshots.

**REQUIRED FIELDS:**
- payment_status (string): "COMPLETED" or "FAILED"
- rejection_reason (string): Required if payment_status is "FAILED"

**BEHAVIOR:**
- When COMPLETED: payment_status → COMPLETED, registration status → CONFIRMED
- When FAILED: payment_status → FAILED, rejection_reason logged

**ACCESS:** Admin only
""",
)
def update_payment_status(
    registration_id: int,
    status_update: PaymentStatusUpdate,
    current_user: Devotee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update payment status for a registration (admin only)."""
    from app.core.dependencies import require_admin

    # Verify admin access
    require_admin(current_user)

    try:
        service = YatraRegistrationService(db)
        result = service.update_payment_status(
            registration_id=registration_id,
            payment_status=status_update.payment_status,
            rejection_reason=status_update.rejection_reason,
        )

        registration_out = RegistrationOut.model_validate(result["registration"]).model_dump(
            mode="json"
        )
        members_out = [
            YatraMemberOut.model_validate(m).model_dump(mode="json") for m in result["members"]
        ]

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "status_code": status.HTTP_200_OK,
                "message": f"Payment status updated to {status_update.payment_status.value}",
                "data": {
                    "registration": registration_out,
                    "members": members_out,
                },
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
    except ValidationError as e:
        logger.error(f"Validation error updating payment status: {e}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                "message": "Invalid payment status update data",
                "data": {"errors": e.errors()},
            },
        )
    except Exception as e:
        logger.error(f"Unexpected error updating payment status: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Failed to update payment status",
                "data": None,
            },
        )


@router.get(
    "/{registration_id}/payment-proof",
    summary="Get Payment Screenshots",
    description="""
View all payment screenshots for a registration.

Returns a list of uploaded payment screenshots with their metadata (name, URL, size, upload date).

**QUERY PARAMETERS:**
- filename (optional): If provided, downloads the specific file instead of listing all files

**BEHAVIOR:**
- Without filename: Returns JSON list of all payment screenshots
- With filename: Returns the file as a download (binary response)

**ACCESS:** Admin or registration owner only
""",
)
def get_payment_screenshots(
    registration_id: int,
    filename: str | None = None,
    current_user: Devotee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all payment screenshots for a registration, or download a specific file."""
    from fastapi.responses import Response

    from app.db.models import UserRole
    from app.services.storage_service import StorageService

    try:
        service = YatraRegistrationService(db)
        is_admin = current_user.role == UserRole.ADMIN

        screenshots = service.get_payment_screenshots(
            registration_id=registration_id, user_id=current_user.id, is_admin=is_admin
        )

        # If filename is provided, download that specific file
        if filename:
            # Find the file in the screenshots list
            matching_file = None
            for screenshot in screenshots:
                # Match by the full gcs_path or just the filename
                if screenshot["gcs_path"].endswith(filename) or screenshot["name"] == filename:
                    matching_file = screenshot
                    break

            if not matching_file:
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={
                        "success": False,
                        "status_code": status.HTTP_404_NOT_FOUND,
                        "message": f"File '{filename}' not found in payment screenshots",
                        "data": None,
                    },
                )

            # Download the file from GCS
            storage_service = StorageService()
            # Extract user_id and full path from gcs_path (format: {user_id}/{group_id}/{uuid}.{ext})
            gcs_path_parts = matching_file["gcs_path"].split("/", 1)
            if len(gcs_path_parts) != 2:
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "success": False,
                        "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                        "message": "Invalid file path format",
                        "data": None,
                    },
                )

            user_id = int(gcs_path_parts[0])
            file_path = gcs_path_parts[1]  # group_id/uuid.ext

            content, content_type = storage_service.download_file(user_id, file_path)

            logger.info(
                f"User {current_user.id} downloaded payment screenshot: {matching_file['gcs_path']}"
            )

            # Return file as streaming response
            return Response(
                content=content,
                media_type=content_type,
                headers={"Content-Disposition": f'attachment; filename="{matching_file["name"]}"'},
            )

        # Otherwise, return list of all screenshots
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "status_code": status.HTTP_200_OK,
                "message": f"Retrieved {len(screenshots)} payment screenshot(s)",
                "data": {
                    "registration_id": registration_id,
                    "screenshots": screenshots,
                },
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
    except Exception as e:
        logger.error(f"Unexpected error getting payment screenshots: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Failed to get payment screenshots",
                "data": None,
            },
        )
