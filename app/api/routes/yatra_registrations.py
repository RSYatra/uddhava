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
