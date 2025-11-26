"""
Devotee Authentication API endpoints.

This module contains all devotee authentication-related routes including signup,
login, email verification, password reset, and JWT token management.
"""

import logging
from datetime import datetime
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse
from pydantic import Field
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.auth_security import (
    auth_security,
    input_validator,
    token_manager,
)
from app.core.config import settings
from app.core.dependencies import require_admin
from app.core.security import create_access_token, get_current_user
from app.db.models import Devotee
from app.db.session import get_db
from app.schemas.auth import LoginRequest, LoginResponse
from app.schemas.devotee import (
    DevoteeOut,
    DevoteeSimpleCreate,
)
from app.schemas.email_verification import (
    EmailVerificationRequest,
    EmailVerificationResponse,
    ResendVerificationRequest,
    ResendVerificationResponse,
    SignupResponse,
)
from app.schemas.password_reset import (
    AdminResetPasswordRequest,
    AdminResetPasswordResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
)
from app.services.devotee_service import DevoteeService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Devotee Authentication"])


# Note: get_db and get_current_user are imported from their centralized locations
# - get_db from app.db.session
# - get_current_user from app.core.security


@router.post(
    "/signup",
    response_model=SignupResponse,
    summary="Register New Devotee Account",
    description=r"""
Register a new devotee with simplified signup process.

**Process Flow:**
```
┌─────────────────────────────────────────────────────────────────┐
│                        SIGNUP PROCESS                           │
└─────────────────────────────────────────────────────────────────┘

    ┌──────────────┐
    │   Request    │
    └──────┬───────┘
           │
           ↓
    ┌──────────────────┐
    │ Schema Validation│ (Pydantic)
    └──────┬───────────┘
           │
           ↓
    ┌──────────────────┐
    │  Rate Limit      │ (3 per 15 min)
    └──────┬───────────┘
           │
           ↓
    ┌──────────────────┐
    │ Email Validation │ (Format + Normalize)
    └──────┬───────────┘
           │
           ↓
    ┌──────────────────┐
    │ Password Check   │ (Complexity + Strength)
    └──────┬───────────┘
           │
           ↓
    ┌──────────────────┐
    │   Sanitization   │ (XSS + SQL Injection)
    └──────┬───────────┘
           │
           ↓
    ┌──────────────────┐
    │ Check Existing   │
    │      User        │
    └──────┬───────────┘
           │
           ├─ Verified? → 409 Error (Login Instead)
           │
           ├─ Unverified? → Resend Email + 409 Error
           │
           ↓ New User
    ┌──────────────────┐
    │  Generate Token  │ (Secure Random)
    └──────┬───────────┘
           │
           ↓
    ┌──────────────────┐
    │  Create Devotee  │ (DB Insert)
    └──────┬───────────┘
           │
           ↓
    ┌──────────────────┐
    │   Send Email     │ (Verification Link)
    └──────┬───────────┘
           │
           ↓
    ┌──────────────────┐
    │  200 Response    │ (Success Message)
    └──────────────────┘
```

**Security & Requirements:**
- Rate limited: 3 attempts per 15 minutes per IP
- Password requirements:
  - Length: Minimum 8 characters
  - Must contain: uppercase (A-Z), lowercase (a-z), digit (0-9), special char
  - Validation pattern: `^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]).{8,128}$`
- Email requirements:
  - Pattern: `^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$`
  - Automatically normalized to lowercase
- Email verification required before login

**Account Creation:**
1. Account created in unverified state
2. Verification email sent (valid for 24 hours)
3. User must verify email via link in email
4. After verification, user can login and complete full profile

**Important Notes:**
- Email is case-insensitive (automatically normalized to lowercase)
- If email exists but unverified, verification email is automatically resent
- Passwords are hashed with bcrypt (never stored in plain text)
    """,
    responses={
        200: {
            "description": "Success - Account created and verification email sent",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "status_code": 200,
                        "message": "Registration successful. Verification email sent. Please check your inbox to verify your email address.",
                        "data": {
                            "user_id": 123,
                            "email": "radha.krishna@example.com",
                            "email_verified": False,
                        },
                    }
                }
            },
        },
        400: {
            "description": "Bad Request - Invalid input or weak password",
            "content": {
                "application/json": {
                    "examples": {
                        "weak_password": {
                            "summary": "Password complexity requirements not met",
                            "value": {
                                "success": False,
                                "status_code": 400,
                                "message": "Password must contain uppercase, lowercase, digit, and special character",
                                "data": None,
                            },
                        },
                        "common_password": {
                            "summary": "Password is too common/weak",
                            "value": {
                                "success": False,
                                "status_code": 400,
                                "message": "Password is too common",
                                "data": None,
                            },
                        },
                        "invalid_email": {
                            "summary": "Email format is invalid",
                            "value": {
                                "success": False,
                                "status_code": 400,
                                "message": "Invalid email format",
                                "data": None,
                            },
                        },
                        "password_too_long": {
                            "summary": "Password exceeds maximum length (DoS prevention)",
                            "value": {
                                "success": False,
                                "status_code": 400,
                                "message": "Password too long",
                                "data": None,
                            },
                        },
                    }
                }
            },
        },
        409: {
            "description": "Conflict - Email already registered",
            "content": {
                "application/json": {
                    "examples": {
                        "verified_user": {
                            "summary": "Email exists and is verified (user should login instead)",
                            "value": {
                                "success": False,
                                "status_code": 409,
                                "message": "A verified devotee with this email already exists",
                                "data": {"email": "user@example.com"},
                            },
                        },
                        "unverified_user": {
                            "summary": "Email exists but unverified (verification email resent automatically)",
                            "value": {
                                "success": False,
                                "status_code": 409,
                                "message": "Devotee exists but is not verified. Verification email sent again.",
                                "data": {"email": "user@example.com"},
                            },
                        },
                    }
                }
            },
        },
        422: {
            "description": "Validation Error - Request schema validation failed",
            "content": {
                "application/json": {
                    "examples": {
                        "missing_field": {
                            "summary": "Required field is missing",
                            "value": {
                                "success": False,
                                "status_code": 422,
                                "message": "Field 'password' is required",
                                "data": None,
                            },
                        },
                        "invalid_email_format": {
                            "summary": "Email format validation failed",
                            "value": {
                                "success": False,
                                "status_code": 422,
                                "message": "Invalid email format",
                                "data": None,
                            },
                        },
                        "name_too_long": {
                            "summary": "Name exceeds 127 character limit",
                            "value": {
                                "success": False,
                                "status_code": 422,
                                "message": "Legal name must not exceed 127 characters",
                                "data": None,
                            },
                        },
                    }
                }
            },
        },
        429: {
            "description": "Rate Limited - Too many requests",
            "content": {
                "application/json": {
                    "examples": {
                        "rate_limit_exceeded": {
                            "summary": "More than 3 signup attempts in 15 minutes",
                            "value": {
                                "success": False,
                                "status_code": 429,
                                "message": "Too many signup attempts from this IP. Please try again later.",
                                "data": {"retry_after_seconds": 900},
                            },
                        },
                        "ip_blocked": {
                            "summary": "IP temporarily blocked for suspicious activity (1 hour block)",
                            "value": {
                                "success": False,
                                "status_code": 429,
                                "message": "IP address temporarily blocked",
                                "data": {"retry_after_seconds": 3600},
                            },
                        },
                    }
                }
            },
        },
        500: {
            "description": "Server Error - System failure (safe to retry)",
            "content": {
                "application/json": {
                    "examples": {
                        "database_error": {
                            "summary": "Database connection or transaction failed",
                            "value": {
                                "success": False,
                                "status_code": 500,
                                "message": "Database error occurred during registration",
                                "data": None,
                            },
                        },
                        "email_service_error": {
                            "summary": "Email service unavailable (user created but email not sent)",
                            "value": {
                                "success": False,
                                "status_code": 500,
                                "message": "Failed to send verification email. Please try again later.",
                                "data": None,
                            },
                        },
                        "unexpected_error": {
                            "summary": "Unexpected system error",
                            "value": {
                                "success": False,
                                "status_code": 500,
                                "message": "An unexpected error occurred during registration",
                                "data": None,
                            },
                        },
                    }
                }
            },
        },
    },
    tags=["Devotee Authentication"],
)
async def devotee_signup(
    request: Request,
    devotee_data: DevoteeSimpleCreate,
    db: Session = Depends(get_db),
):
    """
    Register a new devotee with simplified signup process.

    See the detailed description and response examples above for all scenarios.
    """
    try:
        # Apply rate limiting
        auth_security.check_signup_rate_limit(request)

        # Validate and sanitize inputs from the incoming data
        email = input_validator.validate_email(devotee_data.email)
        password = input_validator.validate_password(devotee_data.password)
        legal_name = input_validator.sanitize_string(devotee_data.legal_name, 127)

        # Create validated devotee data
        validated_devotee_data = DevoteeSimpleCreate(
            legal_name=legal_name,
            email=email,
            password=password,
        )

        service = DevoteeService(db)
        devotee = await service.create_simple_unverified_devotee(validated_devotee_data)

        logger.info(f"Simplified devotee signup successful for email: {email}")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=SignupResponse(
                success=True,
                status_code=status.HTTP_200_OK,
                message="Registration successful. Verification email sent. Please check your inbox to verify your email address.",
                data={
                    "user_id": devotee.id,
                    "email": devotee.email,
                    "email_verified": devotee.email_verified,
                },
            ).model_dump(),
        )

    except HTTPException as e:
        # Convert HTTPException to standardized response
        logger.warning(f"Signup validation failed: {e.detail}")

        # Intelligently add data based on error type
        response_data = None
        if e.status_code == status.HTTP_409_CONFLICT:
            # Conflict: Include email for reference
            response_data = {"email": devotee_data.email}
        elif e.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            # Rate Limited: Include retry information
            if "blocked" in str(e.detail).lower():
                response_data = {"retry_after_seconds": 3600}  # 1 hour for blocked IPs
            else:
                response_data = {"retry_after_seconds": 900}  # 15 minutes for rate limit

        return JSONResponse(
            status_code=e.status_code,
            content=SignupResponse(
                success=False,
                status_code=e.status_code,
                message=e.detail if isinstance(e.detail, str) else str(e.detail),
                data=response_data,
            ).model_dump(),
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error during devotee signup: {e!s}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=SignupResponse(
                success=False,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Database error occurred during registration",
                data=None,
            ).model_dump(),
        )
    except Exception as e:
        logger.error(f"Unexpected error during devotee signup: {e!s}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=SignupResponse(
                success=False,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="An unexpected error occurred during registration",
                data=None,
            ).model_dump(),
        )


@router.post(
    "/complete-profile",
    summary="Complete Devotee Profile",
    description="""
Complete your devotee profile with personal, family, spiritual, and location details.

**REQUIRED FIELDS:**

All required fields must be provided to complete profile registration.

**OPTIONAL FIELDS:**

Optional fields can be skipped but are recommended for a complete profile.

**FILE UPLOADS:**

- **Profile Photo:** Optional, max 5MB, formats: .jpg, .jpeg, .png, .gif, .webp
- **Documents:** Optional, max 5 documents, 5MB each, formats: .pdf, .doc, .docx, .txt
- **Total Limit:** 20MB per user across all files

**AUTHENTICATION:**

Requires valid JWT token (Bearer token) in Authorization header.
    """,
    responses={
        200: {
            "description": "Profile completed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "status_code": 200,
                        "message": "Profile completed successfully",
                        "data": None,
                    }
                }
            },
        },
        400: {
            "description": "Invalid input data or validation error",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "status_code": 400,
                        "message": "Invalid date format. Use YYYY-MM-DD",
                        "data": None,
                    }
                }
            },
        },
        401: {"description": "Not authenticated - missing or invalid token"},
        413: {
            "description": "File too large or total size limit exceeded",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "status_code": 413,
                        "message": "Total file size exceeds 20MB limit",
                        "data": None,
                    }
                }
            },
        },
        422: {"description": "Validation error - incorrect field format"},
    },
    tags=["Devotee Authentication"],
)
async def complete_devotee_profile(
    # REQUIRED: Personal Information
    date_of_birth: Annotated[
        str,
        Form(
            description="Date of birth in YYYY-MM-DD format",
            min_length=10,
            max_length=10,
        ),
        Field(example="1990-05-15"),
    ],
    gender: Annotated[
        str,
        Form(
            description="Gender: M (Male) or F (Female)",
            pattern="^[MF]$",
        ),
        Field(example="M"),
    ],
    marital_status: Annotated[
        str,
        Form(description="Marital status: SINGLE, MARRIED, DIVORCED, WIDOWED, SEPARATED, OTHERS"),
        Field(example="MARRIED"),
    ],
    country_code: Annotated[
        str,
        Form(
            description="Country calling code with + prefix",
            pattern=r"^\+\d{1,4}$",
        ),
        Field(example="+91"),
    ],
    mobile_number: Annotated[
        str,
        Form(
            description="Mobile number (10-15 digits, no spaces or special characters)",
            min_length=10,
            max_length=15,
        ),
        Field(example="9876543210"),
    ],
    father_name: Annotated[
        str,
        Form(
            description="Father's full name",
            max_length=127,
        ),
        Field(example="Ram Kumar Sharma"),
    ],
    mother_name: Annotated[
        str,
        Form(
            description="Mother's full name",
            max_length=127,
        ),
        Field(example="Sita Sharma"),
    ],
    # OPTIONAL: Family Information
    spouse_name: Annotated[
        str | None,
        Form(
            description="Spouse name (required if marital status is MARRIED)",
            max_length=127,
        ),
        Field(default=None, example="Radha Sharma"),
    ] = None,
    date_of_marriage: Annotated[
        str | None,
        Form(description="Date of marriage in YYYY-MM-DD format (required if married)"),
        Field(default=None, example="2015-06-20"),
    ] = None,
    national_id: Annotated[
        str | None,
        Form(
            description="National ID or passport number",
            max_length=50,
        ),
        Field(default=None, example="ABCDE1234F"),
    ] = None,
    # OPTIONAL: Location Information
    address: Annotated[
        str | None,
        Form(
            description="Full residential address",
            max_length=255,
        ),
        Field(default=None, example="123 Main Street, Apartment 4B"),
    ] = None,
    city: Annotated[
        str | None,
        Form(
            description="City name",
            max_length=100,
        ),
        Field(default=None, example="Mumbai"),
    ] = None,
    state_province: Annotated[
        str | None,
        Form(
            description="State or province name",
            max_length=100,
        ),
        Field(default=None, example="Maharashtra"),
    ] = None,
    country: Annotated[
        str | None,
        Form(
            description="Country name",
            max_length=100,
        ),
        Field(default=None, example="India"),
    ] = None,
    postal_code: Annotated[
        str | None,
        Form(
            description="Postal or ZIP code",
            max_length=20,
        ),
        Field(default=None, example="400001"),
    ] = None,
    # OPTIONAL: Spiritual Information
    initiation_status: Annotated[
        str | None,
        Form(description="ISKCON initiation status: ASPIRING, HARINAM, or BRAHMIN"),
        Field(default=None, example="HARINAM"),
    ] = None,
    spiritual_master: Annotated[
        str | None,
        Form(
            description="Name of your spiritual master (Guru)",
            max_length=255,
        ),
        Field(default=None, example="His Holiness Radhanath Swami"),
    ] = None,
    initiation_date: Annotated[
        str | None,
        Form(description="Date of initiation in YYYY-MM-DD format"),
        Field(default=None, example="2018-08-15"),
    ] = None,
    initiation_place: Annotated[
        str | None,
        Form(
            description="Place where you received initiation",
            max_length=127,
        ),
        Field(default=None, example="Vrindavan, India"),
    ] = None,
    spiritual_guide: Annotated[
        str | None,
        Form(
            description="Name of your spiritual guide or counselor",
            max_length=255,
        ),
        Field(default=None, example="Prabhu Krishna Das"),
    ] = None,
    # OPTIONAL: ISKCON Journey
    when_were_you_introduced_to_iskcon: Annotated[
        str | None,
        Form(
            description="When you first learned about ISKCON (year or description)",
            max_length=255,
        ),
        Field(default=None, example="2010"),
    ] = None,
    who_introduced_you_to_iskcon: Annotated[
        str | None,
        Form(
            description="Person who introduced you to ISKCON",
            max_length=255,
        ),
        Field(default=None, example="My friend Prashant"),
    ] = None,
    which_iskcon_center_you_first_connected_to: Annotated[
        str | None,
        Form(
            description="First ISKCON temple or center you visited",
            max_length=255,
        ),
        Field(default=None, example="ISKCON Vrindavan"),
    ] = None,
    # OPTIONAL: Chanting Practice
    chanting_number_of_rounds: Annotated[
        int,
        Form(
            description="Number of rounds you chant daily (default: 16)",
            ge=0,
            le=100,
        ),
        Field(default=16, example=16),
    ] = 16,
    chanting_16_rounds_since: Annotated[
        str | None,
        Form(description="Date when you started chanting 16 rounds daily (YYYY-MM-DD)"),
        Field(default=None, example="2015-01-01"),
    ] = None,
    # OPTIONAL: Education
    devotional_courses: Annotated[
        str | None,
        Form(
            description="List of ISKCON devotional courses completed (comma-separated)",
            max_length=500,
        ),
        Field(default=None, example="Bhakti Shastri, Bhakti Vaibhava"),
    ] = None,
    # OPTIONAL: File Uploads
    profile_photo: UploadFile | None = File(
        default=None,
        description="Profile photo (max 5MB, formats: .jpg, .jpeg, .png, .gif, .webp)",
    ),
    document_1: UploadFile | str | None = File(
        default=None,
        description="Document 1 (max 5MB, formats: .pdf, .doc, .docx, .txt, .jpg, .jpeg, .png, .gif, .webp)",
    ),
    document_2: UploadFile | str | None = File(
        default=None,
        description="Document 2 (max 5MB, formats: .pdf, .doc, .docx, .txt, .jpg, .jpeg, .png, .gif, .webp)",
    ),
    document_3: UploadFile | str | None = File(
        default=None,
        description="Document 3 (max 5MB, formats: .pdf, .doc, .docx, .txt, .jpg, .jpeg, .png, .gif, .webp)",
    ),
    document_4: UploadFile | str | None = File(
        default=None,
        description="Document 4 (max 5MB, formats: .pdf, .doc, .docx, .txt, .jpg, .jpeg, .png, .gif, .webp)",
    ),
    document_5: UploadFile | str | None = File(
        default=None,
        description="Document 5 (max 5MB, formats: .pdf, .doc, .docx, .txt, .jpg, .jpeg, .png, .gif, .webp)",
    ),
    # Authentication and database dependencies
    current_devotee: Devotee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        # Get the authenticated devotee's ID
        user_id = current_devotee.id

        # Validate and sanitize inputs
        father_name = input_validator.sanitize_string(father_name, 127)
        mother_name = input_validator.sanitize_string(mother_name, 127)

        # Validate phone number
        mobile_number = input_validator.validate_phone_number(mobile_number)

        # Sanitize optional fields
        spouse_name = (
            input_validator.sanitize_string(spouse_name or "", 127) if spouse_name else None
        )
        national_id = (
            input_validator.sanitize_string(national_id or "", 50) if national_id else None
        )
        address = input_validator.sanitize_string(address or "", 255) if address else None
        city = input_validator.sanitize_string(city or "", 100) if city else None
        state_province = (
            input_validator.sanitize_string(state_province or "", 100) if state_province else None
        )
        country = input_validator.sanitize_string(country or "", 100) if country else None
        postal_code = (
            input_validator.sanitize_string(postal_code or "", 20) if postal_code else None
        )

        # Sanitize spiritual fields
        spiritual_master = (
            input_validator.sanitize_string(spiritual_master or "", 255)
            if spiritual_master
            else None
        )
        initiation_place = (
            input_validator.sanitize_string(initiation_place or "", 127)
            if initiation_place
            else None
        )
        spiritual_guide = (
            input_validator.sanitize_string(spiritual_guide or "", 127) if spiritual_guide else None
        )
        who_introduced_you_to_iskcon = (
            input_validator.sanitize_string(who_introduced_you_to_iskcon or "", 127)
            if who_introduced_you_to_iskcon
            else None
        )
        which_iskcon_center_you_first_connected_to = (
            input_validator.sanitize_string(which_iskcon_center_you_first_connected_to or "", 127)
            if which_iskcon_center_you_first_connected_to
            else None
        )
        when_were_you_introduced_to_iskcon = (
            input_validator.sanitize_string(when_were_you_introduced_to_iskcon or "", 127)
            if when_were_you_introduced_to_iskcon
            else None
        )

        # Validate chanting rounds (using constant for max rounds)
        MAX_CHANTING_ROUNDS = 200
        if chanting_number_of_rounds < 0 or chanting_number_of_rounds > MAX_CHANTING_ROUNDS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Chanting rounds must be between 0 and {MAX_CHANTING_ROUNDS}",
            )

        # Parse dates with proper error handling
        def parse_date_safely(date_str: str, field_name: str):
            """Parse date string safely with descriptive error message."""
            if not date_str or date_str.lower() in [
                "string",
                "null",
                "none",
                "",
            ]:
                return None
            try:
                return datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid date format for {field_name}. \
                    Expected YYYY-MM-DD, got: {date_str}",
                )

        # Validate required date_of_birth first
        if not date_of_birth or date_of_birth.lower() in [
            "string",
            "null",
            "none",
            "",
        ]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="date_of_birth is required and must be in YYYY-MM-DD format",
            )
        parsed_date_of_birth = parse_date_safely(date_of_birth, "date_of_birth")
        parsed_date_of_marriage = parse_date_safely(date_of_marriage, "date_of_marriage")
        parsed_initiation_date = parse_date_safely(initiation_date, "initiation_date")
        parsed_chanting_since = parse_date_safely(
            chanting_16_rounds_since, "chanting_16_rounds_since"
        )

        # For ISKCON introduction, treat as text if not a valid date
        parsed_introduced_date = None
        if (
            when_were_you_introduced_to_iskcon
            and when_were_you_introduced_to_iskcon.lower() not in ["string", "null", "none", ""]
        ):
            try:
                parsed_introduced_date = datetime.strptime(
                    when_were_you_introduced_to_iskcon, "%Y-%m-%d"
                ).date()
            except ValueError:
                # Keep as text in the original field, don't convert to date
                pass

        service = DevoteeService(db)

        # Create profile completion data with authenticated user ID
        profile_data = {
            "date_of_birth": parsed_date_of_birth,
            "gender": gender,
            "marital_status": marital_status,
            "country_code": country_code,
            "mobile_number": mobile_number,
            "father_name": father_name,
            "mother_name": mother_name,
            "spouse_name": spouse_name,
            "date_of_marriage": parsed_date_of_marriage,
            "national_id": national_id,
            "address": address,
            "city": city,
            "state_province": state_province,
            "country": country,
            "postal_code": postal_code,
            "initiation_status": initiation_status,
            "spiritual_master": spiritual_master,
            "initiation_date": parsed_initiation_date,
            "initiation_place": initiation_place,
            "spiritual_guide": spiritual_guide,
            "when_were_you_introduced_to_iskcon": parsed_introduced_date,
            "who_introduced_you_to_iskcon": who_introduced_you_to_iskcon,
            "which_iskcon_center_you_first_connected_to": (
                which_iskcon_center_you_first_connected_to
            ),
            "chanting_number_of_rounds": chanting_number_of_rounds,
            "chanting_16_rounds_since": parsed_chanting_since,
            "devotional_courses": devotional_courses,
        }

        # Collect uploaded files
        # Note: curl/Swagger UI may send empty strings for unselected file fields
        uploaded_documents = []
        for doc in [document_1, document_2, document_3, document_4, document_5]:
            # Check if it's an UploadFile by checking for filename attribute (more reliable than isinstance)
            if doc and hasattr(doc, "filename") and doc.filename:
                uploaded_documents.append(doc)

        logger.info(f"Collected {len(uploaded_documents)} document(s) for upload")
        if profile_photo and hasattr(profile_photo, "filename") and profile_photo.filename:
            logger.info(f"Profile photo received: {profile_photo.filename}")

        # Complete the profile using the authenticated user's ID with files
        updated_devotee = await service.complete_devotee_profile(
            user_id=user_id,
            profile_data=profile_data,
            profile_photo=profile_photo
            if profile_photo and hasattr(profile_photo, "filename") and profile_photo.filename
            else None,
            uploaded_files=uploaded_documents if uploaded_documents else None,
        )

        files_count = (
            1
            if profile_photo and hasattr(profile_photo, "filename") and profile_photo.filename
            else 0
        ) + len(uploaded_documents)
        logger.info(f"Profile completed successfully for user {user_id} with {files_count} file(s)")

        # Convert devotee to response schema
        devotee_data = DevoteeOut.model_validate(updated_devotee).model_dump(mode="json")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "status_code": 200,
                "message": f"Profile completed successfully. {files_count} file(s) uploaded.",
                "data": devotee_data,
            },
        )

    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={
                "success": False,
                "status_code": e.status_code,
                "message": e.detail if isinstance(e.detail, str) else str(e.detail),
                "data": None,
            },
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error during profile completion: {e!s}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "status_code": 500,
                "message": "Database error occurred during profile completion",
                "data": None,
            },
        )
    except Exception as e:
        logger.error(f"Unexpected error during profile completion: {e!s}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "status_code": 500,
                "message": "An unexpected error occurred during profile completion",
                "data": None,
            },
        )


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login to Devotee Account",
    description="""
Login with email and password to receive authentication token.

**Security Features:**
- Rate limiting: 5 attempts per 15 minutes per IP/email combination
- Email verification required before login
- Bcrypt password verification
- Secure error messages (no information leakage)
- Failed attempt tracking
- Automatic IP blocking for suspicious activity

**Requirements:**
- Email must be verified
- Valid credentials required
- Account must not be locked

**Authentication Flow:**
1. Submit email and password
2. System validates credentials
3. Checks email verification status
4. Generates JWT token (expires in 1 hour)
5. Returns token with user info
    """,
    responses={
        200: {
            "description": "Success - Login successful, JWT token provided",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "status_code": 200,
                        "message": "Login successful",
                        "data": {
                            "user_id": 123,
                            "email": "radha.krishna@example.com",
                            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "token_type": "bearer",
                            "expires_in": 3600,
                        },
                    }
                }
            },
        },
        400: {
            "description": "Bad Request - Email not verified",
            "content": {
                "application/json": {
                    "examples": {
                        "email_not_verified": {
                            "summary": "Email verification required",
                            "value": {
                                "success": False,
                                "status_code": 400,
                                "message": "Email must be verified before login. Please check your inbox for verification link.",
                                "data": {"email": "user@example.com"},
                            },
                        },
                        "invalid_email": {
                            "summary": "Invalid email format",
                            "value": {
                                "success": False,
                                "status_code": 400,
                                "message": "Invalid email format",
                                "data": None,
                            },
                        },
                    }
                }
            },
        },
        401: {
            "description": "Unauthorized - Invalid credentials",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_credentials": {
                            "summary": "Wrong email or password",
                            "value": {
                                "success": False,
                                "status_code": 401,
                                "message": "Invalid credentials",
                                "data": None,
                            },
                        },
                    }
                }
            },
        },
        429: {
            "description": "Rate Limited - Too many login attempts",
            "content": {
                "application/json": {
                    "examples": {
                        "rate_limit_exceeded": {
                            "summary": "More than 5 login attempts in 15 minutes",
                            "value": {
                                "success": False,
                                "status_code": 429,
                                "message": "Too many login attempts. Please try again later.",
                                "data": {"retry_after_seconds": 900},
                            },
                        },
                    }
                }
            },
        },
        500: {
            "description": "Server Error - System failure",
            "content": {
                "application/json": {
                    "examples": {
                        "database_error": {
                            "summary": "Database connection failed",
                            "value": {
                                "success": False,
                                "status_code": 500,
                                "message": "Database error occurred during login",
                                "data": None,
                            },
                        },
                    }
                }
            },
        },
    },
    tags=["Devotee Authentication"],
)
async def devotee_login(
    request: Request,
    login_data: LoginRequest,
    db: Session = Depends(get_db),
):
    """
    Login devotee with email and password.

    Returns JWT access token for authenticated devotee.
    Devotee must have verified email to login.
    """
    # Initialize email variable for exception handling
    email = login_data.email

    try:
        # Validate and sanitize email
        email = input_validator.validate_email(login_data.email)

        # Apply rate limiting before authentication attempt
        auth_security.check_login_rate_limit(request, email)

        service = DevoteeService(db)

        # Authenticate devotee (returns None if invalid credentials)
        devotee = service.authenticate_devotee(email, login_data.password)
        if not devotee:
            # Use generic error message to prevent email enumeration
            logger.warning(f"Failed login attempt for email: {email}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content=LoginResponse(
                    success=False,
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    message="Invalid credentials",
                    data=None,
                ).model_dump(),
            )

        # Clear rate limiting on successful login
        auth_security.record_successful_login(request, email)

        # Generate JWT token
        access_token = create_access_token(
            data={
                "sub": str(devotee.id),
                "email": devotee.email,
                "role": "devotee",
            }
        )

        # Calculate expires_in (None if token never expires)
        expires_in_seconds = (
            settings.jwt_access_token_expire_minutes * 60
            if settings.jwt_access_token_expire_minutes is not None
            else None
        )

        logger.info(f"Devotee login successful for email: {email}")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=LoginResponse(
                success=True,
                status_code=status.HTTP_200_OK,
                message="Login successful",
                data={
                    "user_id": devotee.id,
                    "email": devotee.email,
                    "access_token": access_token,
                    "token_type": "bearer",
                    "expires_in": expires_in_seconds,
                },
            ).model_dump(),
        )

    except HTTPException as e:
        # Convert HTTPException to standardized response
        logger.warning(f"Login failed: {e.detail}")

        # Intelligently add data based on error type
        response_data = None
        if e.status_code == status.HTTP_400_BAD_REQUEST:
            # Email not verified - include email for reference
            response_data = {"email": email}
        elif e.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            # Rate limited - include retry information
            response_data = {"retry_after_seconds": 900}

        # Handle specific error messages
        message = e.detail if isinstance(e.detail, str) else str(e.detail)
        if "Email must be verified" in message:
            message = "Email must be verified before login. Please check your inbox for verification link."

        return JSONResponse(
            status_code=e.status_code,
            content=LoginResponse(
                success=False,
                status_code=e.status_code,
                message=message,
                data=response_data,
            ).model_dump(),
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error during devotee login: {e!s}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=LoginResponse(
                success=False,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Database error occurred during login",
                data=None,
            ).model_dump(),
        )
    except Exception as e:
        logger.error(f"Unexpected error during devotee login: {e!s}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=LoginResponse(
                success=False,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="An unexpected error occurred during login",
                data=None,
            ).model_dump(),
        )


@router.post(
    "/verify-email",
    response_model=EmailVerificationResponse,
    summary="Verify Email Address",
    description="""
Verify devotee's email address using the verification token sent via email.

**Process Flow:**
```
┌─────────────────────────────────────────────────────────────────┐
│                   EMAIL VERIFICATION PROCESS                    │
└─────────────────────────────────────────────────────────────────┘

    ┌──────────────┐
    │ Click Email  │
    │     Link     │
    └──────┬───────┘
           │
           ↓
    ┌──────────────────┐
    │ Schema Validation│ (Pydantic)
    └──────┬───────────┘
           │
           ↓
    ┌──────────────────┐
    │ Token Format     │ (Length + Pattern)
    │   Validation     │
    └──────┬───────────┘
           │
           ↓
    ┌──────────────────┐
    │ Find User by     │
    │     Token        │
    └──────┬───────────┘
           │
           ├─ Not Found? → 404 Error
           │
           ├─ Already Verified? → 400 Error
           │
           ├─ Token Expired? → 400 Error
           │
           ↓ Valid Token
    ┌──────────────────┐
    │ Mark as Verified │ (DB Update)
    └──────┬───────────┘
           │
           ↓
    ┌──────────────────┐
    │   Clear Token    │
    └──────┬───────────┘
           │
           ↓
    ┌──────────────────┐
    │ Send Success     │ (Confirmation Email)
    │     Email        │
    └──────┬───────────┘
           │
           ↓
    ┌──────────────────┐
    │  200 Response    │ (Can Now Login)
    └──────────────────┘
```

**Security Features:**
- Token format validation (32-256 characters)
- Token expiration checks (24 hours validity)
- One-time use tokens (cleared after verification)
- Secure error messages
- Database transaction safety

**Token Requirements:**
- Length: 32-256 characters
- Format: Alphanumeric with special characters
- Validity: 24 hours from signup
- Single use only

**After Verification:**
- User can login with their credentials
- Verification token is invalidated
- Confirmation email is sent
- User can complete their full profile
    """,
    responses={
        200: {
            "description": "Success - Email verified successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "status_code": 200,
                        "message": "Email verified successfully. You can now login to your account.",
                        "data": {
                            "email": "radha.krishna@example.com",
                            "email_verified": True,
                        },
                    }
                }
            },
        },
        400: {
            "description": "Bad Request - Invalid token or already verified",
            "content": {
                "application/json": {
                    "examples": {
                        "already_verified": {
                            "summary": "Email already verified",
                            "value": {
                                "success": False,
                                "status_code": 400,
                                "message": "Email is already verified",
                                "data": None,
                            },
                        },
                        "token_expired": {
                            "summary": "Verification token expired (24 hours)",
                            "value": {
                                "success": False,
                                "status_code": 400,
                                "message": "Verification token has expired",
                                "data": None,
                            },
                        },
                        "invalid_token_format": {
                            "summary": "Token format is invalid",
                            "value": {
                                "success": False,
                                "status_code": 400,
                                "message": "Invalid verification token format",
                                "data": None,
                            },
                        },
                    }
                }
            },
        },
        404: {
            "description": "Not Found - Token not found in database",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "status_code": 404,
                        "message": "Invalid or expired verification token",
                        "data": None,
                    }
                }
            },
        },
        422: {
            "description": "Validation Error - Invalid request format",
            "content": {
                "application/json": {
                    "examples": {
                        "missing_token": {
                            "summary": "Token field is missing",
                            "value": {
                                "success": False,
                                "status_code": 422,
                                "message": "Field 'token' is required",
                                "data": None,
                            },
                        },
                        "token_too_short": {
                            "summary": "Token is too short",
                            "value": {
                                "success": False,
                                "status_code": 422,
                                "message": "Token must be at least 32 characters",
                                "data": None,
                            },
                        },
                    }
                }
            },
        },
        500: {
            "description": "Server Error - System failure",
            "content": {
                "application/json": {
                    "examples": {
                        "database_error": {
                            "summary": "Database connection failed",
                            "value": {
                                "success": False,
                                "status_code": 500,
                                "message": "Database error occurred during email verification",
                                "data": None,
                            },
                        },
                        "unexpected_error": {
                            "summary": "Unexpected system error",
                            "value": {
                                "success": False,
                                "status_code": 500,
                                "message": "An unexpected error occurred during email verification",
                                "data": None,
                            },
                        },
                    }
                }
            },
        },
    },
    tags=["Devotee Authentication"],
)
async def verify_devotee_email(
    request_obj: Request,
    request: EmailVerificationRequest,
    db: Session = Depends(get_db),
):
    """
    Verify devotee's email address using verification token.

    See the detailed description and response examples above for all scenarios.
    """
    try:
        logger.info("Starting email verification process")

        # Validate token format to prevent injection attacks
        if not token_manager.validate_token_format(request.token):
            logger.warning("Token format validation failed")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=EmailVerificationResponse(
                    success=False,
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="Invalid verification token format",
                    data=None,
                ).model_dump(),
            )

        service = DevoteeService(db)
        verified_email = await service.verify_devotee_email(request.token)

        logger.info(f"Email verification successful for: {verified_email}")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=EmailVerificationResponse(
                success=True,
                status_code=status.HTTP_200_OK,
                message="Email verified successfully. You can now login to your account.",
                data={
                    "email": verified_email,
                    "email_verified": True,
                },
            ).model_dump(),
        )

    except HTTPException as e:
        # Convert HTTPException to standardized response
        logger.warning(f"Email verification failed: {e.detail}")
        return JSONResponse(
            status_code=e.status_code,
            content=EmailVerificationResponse(
                success=False,
                status_code=e.status_code,
                message=e.detail if isinstance(e.detail, str) else str(e.detail),
                data=None,
            ).model_dump(),
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error during email verification: {e!s}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=EmailVerificationResponse(
                success=False,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Database error occurred during email verification",
                data=None,
            ).model_dump(),
        )
    except Exception as e:
        logger.error(f"Unexpected error during email verification: {e!s}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=EmailVerificationResponse(
                success=False,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="An unexpected error occurred during email verification",
                data=None,
            ).model_dump(),
        )


@router.post(
    "/resend-verification",
    response_model=ResendVerificationResponse,
    summary="Resend Verification Email",
    description="""
Resend email verification link to a devotee.

**Use Cases:**
- Verification email not received
- Verification token expired (24 hours)
- Email went to spam folder
- User lost the original email

**Process:**
1. Validates email format
2. Checks if user exists
3. Checks if already verified
4. Generates new verification token
5. Sends new verification email

**Security:**
- Rate limited to prevent abuse
- New token invalidates old token
- 24-hour expiration
- Generic error messages (no email enumeration)
    """,
    responses={
        200: {
            "description": "Success - Verification email resent",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "status_code": 200,
                        "message": "Verification email sent. Please check your inbox and spam folder.",
                        "data": {
                            "email": "radha.krishna@example.com",
                        },
                    }
                }
            },
        },
        400: {
            "description": "Bad Request - Email already verified or invalid",
            "content": {
                "application/json": {
                    "examples": {
                        "already_verified": {
                            "summary": "Email already verified",
                            "value": {
                                "success": False,
                                "status_code": 400,
                                "message": "Email is already verified. You can login now.",
                                "data": None,
                            },
                        },
                        "resend_failed": {
                            "summary": "Failed to resend email",
                            "value": {
                                "success": False,
                                "status_code": 400,
                                "message": "Failed to resend verification email",
                                "data": None,
                            },
                        },
                    }
                }
            },
        },
        422: {
            "description": "Validation Error - Invalid email format",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "status_code": 422,
                        "message": "Invalid email format",
                        "data": None,
                    }
                }
            },
        },
        500: {
            "description": "Server Error - System failure",
            "content": {
                "application/json": {
                    "examples": {
                        "database_error": {
                            "summary": "Database connection failed",
                            "value": {
                                "success": False,
                                "status_code": 500,
                                "message": "Database error occurred while resending verification email",
                                "data": None,
                            },
                        },
                        "email_service_error": {
                            "summary": "Email service unavailable",
                            "value": {
                                "success": False,
                                "status_code": 500,
                                "message": "Failed to send verification email. Please try again later.",
                                "data": None,
                            },
                        },
                    }
                }
            },
        },
    },
    tags=["Devotee Authentication"],
)
async def resend_devotee_verification(
    request_obj: Request,
    request: ResendVerificationRequest,
    db: Session = Depends(get_db),
):
    """
    Resend email verification to devotee.

    See the detailed description and response examples above for all scenarios.
    """
    try:
        # Validate and sanitize email
        email = input_validator.validate_email(request.email)

        service = DevoteeService(db)
        success = await service.resend_verification_email(email)

        if not success:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=ResendVerificationResponse(
                    success=False,
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="Failed to resend verification email",
                    data=None,
                ).model_dump(),
            )

        logger.info(f"Verification email resent to: {email}")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=ResendVerificationResponse(
                success=True,
                status_code=status.HTTP_200_OK,
                message="Verification email sent. Please check your inbox and spam folder.",
                data={"email": email},
            ).model_dump(),
        )

    except HTTPException as e:
        # Convert HTTPException to standardized response
        logger.warning(f"Resend verification failed: {e.detail}")
        return JSONResponse(
            status_code=e.status_code,
            content=ResendVerificationResponse(
                success=False,
                status_code=e.status_code,
                message=e.detail if isinstance(e.detail, str) else str(e.detail),
                data=None,
            ).model_dump(),
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error during resend verification: {e!s}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ResendVerificationResponse(
                success=False,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Database error occurred while resending verification email",
                data=None,
            ).model_dump(),
        )
    except Exception as e:
        logger.error(f"Unexpected error during resend verification: {e!s}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ResendVerificationResponse(
                success=False,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="An unexpected error occurred while resending verification email",
                data=None,
            ).model_dump(),
        )


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    summary="Request Password Reset",
    description="""
Request a password reset link via email.

**Process Flow:**
```
┌─────────────────────────────────────────────────────────────────┐
│                   FORGOT PASSWORD PROCESS                       │
└─────────────────────────────────────────────────────────────────┘

    ┌──────────────┐
    │   Request    │
    │    Reset     │
    └──────┬───────┘
           │
           ↓
    ┌──────────────────┐
    │ Schema Validation│ (Pydantic)
    └──────┬───────────┘
           │
           ↓
    ┌──────────────────┐
    │ Email Validation │ (Format + Normalize)
    └──────┬───────────┘
           │
           ↓
    ┌──────────────────┐
    │  Rate Limiting   │ (3 per 15 min)
    └──────┬───────────┘
           │
           ↓
    ┌──────────────────┐
    │   Find User      │
    └──────┬───────────┘
           │
           ├─ Not Found? → Return Generic Success (Security)
           │
           ├─ Not Verified? → 400 Error
           │
           ↓ Verified User
    ┌──────────────────┐
    │  Generate Token  │ (Secure Random)
    └──────┬───────────┘
           │
           ↓
    ┌──────────────────┐
    │   Save Token     │ (1 hour expiry)
    └──────┬───────────┘
           │
           ↓
    ┌──────────────────┐
    │   Send Email     │ (Reset Link)
    └──────┬───────────┘
           │
           ↓
    ┌──────────────────┐
    │  200 Response    │ (Generic Message)
    └──────────────────┘
```

**Security Features:**
- Rate limiting: 3 attempts per 15 minutes per IP/email
- Generic response (no email enumeration)
- Email verification required
- Secure token generation (32 bytes URL-safe)
- Token expiration (1 hour)
- One-time use tokens

**Requirements:**
- Valid email format
- Email must be verified
- User must exist in system

**Important Notes:**
- Response is always generic for security (doesn't reveal if email exists)
- Only verified users receive reset emails
- Reset link expires in 1 hour
- Token is cleared after successful use
    """,
    responses={
        200: {
            "description": "Success - Generic response for security",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "status_code": 200,
                        "message": "If this email is registered and verified, you will receive password reset instructions.",
                        "data": {
                            "email": "radha.krishna@example.com",
                        },
                    }
                }
            },
        },
        400: {
            "description": "Bad Request - Email not verified",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "status_code": 400,
                        "message": "Email must be verified before password reset",
                        "data": None,
                    }
                }
            },
        },
        422: {
            "description": "Validation Error - Invalid email format",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_email": {
                            "summary": "Email format validation failed",
                            "value": {
                                "success": False,
                                "status_code": 422,
                                "message": "Invalid email format",
                                "data": None,
                            },
                        },
                        "missing_email": {
                            "summary": "Email field is missing",
                            "value": {
                                "success": False,
                                "status_code": 422,
                                "message": "Field 'email' is required",
                                "data": None,
                            },
                        },
                    }
                }
            },
        },
        429: {
            "description": "Rate Limited - Too many requests",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "status_code": 429,
                        "message": "Too many password reset requests. Please try again later.",
                        "data": {"retry_after_seconds": 900},
                    }
                }
            },
        },
        500: {
            "description": "Server Error - System failure",
            "content": {
                "application/json": {
                    "examples": {
                        "database_error": {
                            "summary": "Database connection failed",
                            "value": {
                                "success": False,
                                "status_code": 500,
                                "message": "Database error occurred while sending password reset email",
                                "data": None,
                            },
                        },
                        "email_service_error": {
                            "summary": "Email service unavailable",
                            "value": {
                                "success": False,
                                "status_code": 500,
                                "message": "Failed to send password reset email. Please try again later.",
                                "data": None,
                            },
                        },
                    }
                }
            },
        },
    },
    tags=["Devotee Authentication"],
)
async def devotee_forgot_password(
    request_obj: Request,
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    """
    Send password reset email to devotee.

    See the detailed description and response examples above for all scenarios.
    """
    try:
        # Validate and sanitize email
        email = input_validator.validate_email(request.email)

        # Apply rate limiting for password reset requests
        auth_security.check_password_reset_rate_limit(request_obj, email)

        service = DevoteeService(db)
        await service.send_password_reset_email(email)

        logger.info("Password reset email process completed")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=ForgotPasswordResponse(
                success=True,
                status_code=status.HTTP_200_OK,
                message="Password reset email sent successfully",
                data={"email": email},
            ).model_dump(),
        )

    except HTTPException as e:
        # Convert HTTPException to standardized response
        # This catches email service errors with proper status codes
        logger.warning(f"Forgot password failed with HTTP {e.status_code}: {e.detail}")

        # Intelligently add data based on error type
        response_data = None
        if e.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            response_data = {"retry_after_seconds": 900}

        return JSONResponse(
            status_code=e.status_code,
            content=ForgotPasswordResponse(
                success=False,
                status_code=e.status_code,
                message=e.detail if isinstance(e.detail, str) else str(e.detail),
                data=response_data,
            ).model_dump(),
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error during forgot password: {type(e).__name__}: {e!s}")
        logger.exception("Full database error traceback:")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ForgotPasswordResponse(
                success=False,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Database error occurred while processing password reset",
                data=None,
            ).model_dump(),
        )
    except Exception as e:
        logger.error(f"Unexpected error during forgot password: {type(e).__name__}: {e!s}")
        logger.exception("Full error traceback:")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ForgotPasswordResponse(
                success=False,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"An unexpected error occurred: {type(e).__name__}. Please try again or contact support.",
                data=None,
            ).model_dump(),
        )


@router.post(
    "/reset-password",
    response_model=ResetPasswordResponse,
    summary="Reset Password with Token",
    description="""
Reset devotee's password using the reset token from email.

**Process Flow:**
```
┌─────────────────────────────────────────────────────────────────┐
│                   RESET PASSWORD PROCESS                        │
└─────────────────────────────────────────────────────────────────┘

    ┌──────────────┐
    │ Click Email  │
    │     Link     │
    └──────┬───────┘
           │
           ↓
    ┌──────────────────┐
    │ Schema Validation│ (Pydantic)
    └──────┬───────────┘
           │
           ↓
    ┌──────────────────┐
    │ Token Format     │ (32-256 chars)
    │   Validation     │
    └──────┬───────────┘
           │
           ↓
    ┌──────────────────┐
    │  Password Check  │ (Strength + Complexity)
    └──────┬───────────┘
           │
           ↓
    ┌──────────────────┐
    │ Find User by     │
    │     Token        │
    └──────┬───────────┘
           │
           ├─ Not Found? → 404 Error
           │
           ├─ Token Expired? → 400 Error
           │
           ↓ Valid Token
    ┌──────────────────┐
    │  Hash Password   │ (Bcrypt)
    └──────┬───────────┘
           │
           ↓
    ┌──────────────────┐
    │ Update Password  │ (DB Update)
    └──────┬───────────┘
           │
           ↓
    ┌──────────────────┐
    │   Clear Token    │
    └──────┬───────────┘
           │
           ↓
    ┌──────────────────┐
    │  200 Response    │ (Can Now Login)
    └──────────────────┘
```

**Security Features:**
- Token format validation (32-256 characters)
- Password strength validation (uppercase, lowercase, digit, special char)
- Token expiration checks (1 hour validity)
- One-time use tokens (cleared after reset)
- Secure error messages
- Bcrypt password hashing

**Password Requirements:**
- Length: 8-128 characters
- Must contain:
  - Uppercase letter (A-Z)
  - Lowercase letter (a-z)
  - Digit (0-9)
  - Special character (!@#$%^&*()_+-=[]{}|;:,.<>?)

**After Reset:**
- User can login with new password
- Reset token is invalidated
- Old password no longer works
- User receives confirmation email
    """,
    responses={
        200: {
            "description": "Success - Password reset successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "status_code": 200,
                        "message": "Password reset successful. You can now login with your new password.",
                        "data": {
                            "email": "radha.krishna@example.com",
                        },
                    }
                }
            },
        },
        400: {
            "description": "Bad Request - Token expired or weak password",
            "content": {
                "application/json": {
                    "examples": {
                        "token_expired": {
                            "summary": "Reset token expired (1 hour)",
                            "value": {
                                "success": False,
                                "status_code": 400,
                                "message": "Reset token has expired",
                                "data": None,
                            },
                        },
                        "weak_password": {
                            "summary": "Password doesn't meet requirements",
                            "value": {
                                "success": False,
                                "status_code": 400,
                                "message": "Password must contain uppercase, lowercase, digit, and special character",
                                "data": None,
                            },
                        },
                        "invalid_token_format": {
                            "summary": "Token format is invalid",
                            "value": {
                                "success": False,
                                "status_code": 400,
                                "message": "Invalid reset token format",
                                "data": None,
                            },
                        },
                    }
                }
            },
        },
        404: {
            "description": "Not Found - Token not found in database",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "status_code": 404,
                        "message": "Invalid reset token",
                        "data": None,
                    }
                }
            },
        },
        422: {
            "description": "Validation Error - Invalid request format",
            "content": {
                "application/json": {
                    "examples": {
                        "missing_token": {
                            "summary": "Token field is missing",
                            "value": {
                                "success": False,
                                "status_code": 422,
                                "message": "Field 'token' is required",
                                "data": None,
                            },
                        },
                        "token_too_short": {
                            "summary": "Token is too short",
                            "value": {
                                "success": False,
                                "status_code": 422,
                                "message": "Token must be at least 32 characters",
                                "data": None,
                            },
                        },
                        "password_too_short": {
                            "summary": "Password is too short",
                            "value": {
                                "success": False,
                                "status_code": 422,
                                "message": "Password must be at least 8 characters",
                                "data": None,
                            },
                        },
                    }
                }
            },
        },
        500: {
            "description": "Server Error - System failure",
            "content": {
                "application/json": {
                    "examples": {
                        "database_error": {
                            "summary": "Database connection failed",
                            "value": {
                                "success": False,
                                "status_code": 500,
                                "message": "Database error occurred during password reset",
                                "data": None,
                            },
                        },
                        "unexpected_error": {
                            "summary": "Unexpected system error",
                            "value": {
                                "success": False,
                                "status_code": 500,
                                "message": "An unexpected error occurred during password reset",
                                "data": None,
                            },
                        },
                    }
                }
            },
        },
    },
    tags=["Devotee Authentication"],
)
async def devotee_reset_password(
    request_obj: Request,
    request: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    """
    Reset devotee's password using reset token.

    See the detailed description and response examples above for all scenarios.
    """
    try:
        # Validate token format
        if not token_manager.validate_token_format(request.token):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=ResetPasswordResponse(
                    success=False,
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="Invalid reset token format",
                    data=None,
                ).model_dump(),
            )

        # Validate new password strength
        new_password = input_validator.validate_password(request.new_password)

        service = DevoteeService(db)
        success = service.reset_password_with_token(request.token, new_password)

        if not success:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=ResetPasswordResponse(
                    success=False,
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="Invalid reset token",
                    data=None,
                ).model_dump(),
            )

        # Get devotee email for response (token is now cleared)
        logger.info("Password reset successful")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=ResetPasswordResponse(
                success=True,
                status_code=status.HTTP_200_OK,
                message="Password reset successful. You can now login with your new password.",
                data=None,  # Don't expose email for security
            ).model_dump(),
        )

    except HTTPException as e:
        # Convert HTTPException to standardized response
        logger.warning(f"Password reset failed: {e.detail}")
        return JSONResponse(
            status_code=e.status_code,
            content=ResetPasswordResponse(
                success=False,
                status_code=e.status_code,
                message=e.detail if isinstance(e.detail, str) else str(e.detail),
                data=None,
            ).model_dump(),
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error during password reset: {e!s}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ResetPasswordResponse(
                success=False,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Database error occurred during password reset",
                data=None,
            ).model_dump(),
        )
    except Exception as e:
        logger.error(f"Unexpected error during password reset: {e!s}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ResetPasswordResponse(
                success=False,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="An unexpected error occurred during password reset",
                data=None,
            ).model_dump(),
        )


@router.post(
    "/admin/reset-password",
    response_model=AdminResetPasswordResponse,
    summary="Admin Reset Devotee Password",
    description="""
Reset any devotee's password (admin only).

**Use Cases:**
- Devotee forgot password and has no email access
- Devotee locked out of account
- Emergency password reset required
- Support ticket resolution

**Process:**
```
┌─────────────────────────────────────────────────────────────────┐
│               ADMIN PASSWORD RESET PROCESS                      │
└─────────────────────────────────────────────────────────────────┘

    ┌──────────────┐
    │ Admin Request│
    └──────┬───────┘
           │
           ↓
    ┌──────────────────┐
    │ Auth Check       │ (Admin role required)
    └──────┬───────────┘
           │
           ↓
    ┌──────────────────┐
    │ Schema Validation│ (Pydantic)
    └──────┬───────────┘
           │
           ↓
    ┌──────────────────┐
    │  Password Check  │ (Strength + Complexity)
    └──────┬───────────┘
           │
           ↓
    ┌──────────────────┐
    │   Find Devotee   │ (By ID)
    └──────┬───────────┘
           │
           ├─ Not Found? → 404 Error
           │
           ↓ Found
    ┌──────────────────┐
    │  Hash Password   │ (Bcrypt)
    └──────┬───────────┘
           │
           ↓
    ┌──────────────────┐
    │ Update Password  │ (DB Update)
    └──────┬───────────┘
           │
           ↓
    ┌──────────────────┐
    │   Audit Log      │ (Track admin action)
    └──────┬───────────┘
           │
           ↓
    ┌──────────────────┐
    │  200 Response    │ (Success)
    └──────────────────┘
```

**Security Features:**
- Requires admin authentication (admin role)
- Password strength validation
- Audit logging (tracks which admin reset which devotee)
- Bcrypt password hashing
- No token/email required (direct DB update)

**Password Requirements:**
- Length: 8-128 characters
- Must contain: uppercase, lowercase, digit, special character

**Important Notes:**
- Only admins can use this endpoint
- Action is logged for audit trail
- Devotee is NOT notified (admin responsible for communication)
- No verification email sent
- Password is effective immediately
    """,
    responses={
        200: {
            "description": "Success - Password reset by admin",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "status_code": 200,
                        "message": "Password reset successful by admin",
                        "data": {
                            "devotee_id": 123,
                            "admin_id": 1,
                        },
                    }
                }
            },
        },
        400: {
            "description": "Bad Request - Weak password",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "status_code": 400,
                        "message": "Password must contain uppercase, lowercase, digit, and special character",
                        "data": None,
                    }
                }
            },
        },
        401: {
            "description": "Unauthorized - Not authenticated",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "status_code": 401,
                        "message": "Not authenticated",
                        "data": None,
                    }
                }
            },
        },
        403: {
            "description": "Forbidden - Not an admin",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "status_code": 403,
                        "message": "Admin access required",
                        "data": None,
                    }
                }
            },
        },
        404: {
            "description": "Not Found - Devotee not found",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "status_code": 404,
                        "message": "Devotee not found",
                        "data": None,
                    }
                }
            },
        },
        422: {
            "description": "Validation Error - Invalid input",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_devotee_id": {
                            "summary": "Devotee ID must be positive",
                            "value": {
                                "success": False,
                                "status_code": 422,
                                "message": "Devotee ID must be greater than 0",
                                "data": None,
                            },
                        },
                        "password_too_short": {
                            "summary": "Password too short",
                            "value": {
                                "success": False,
                                "status_code": 422,
                                "message": "Password must be at least 8 characters",
                                "data": None,
                            },
                        },
                    }
                }
            },
        },
        500: {
            "description": "Server Error - System failure",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "status_code": 500,
                        "message": "Database error occurred during admin password reset",
                        "data": None,
                    }
                }
            },
        },
    },
)
async def admin_reset_devotee_password(
    request_obj: Request,
    request: AdminResetPasswordRequest,
    db: Session = Depends(get_db),
    admin: Devotee = Depends(require_admin),
):
    """
    Admin endpoint to reset any devotee's password.

    See the detailed description and response examples above for all scenarios.
    """
    try:
        # Validate password strength (Pydantic validator already called)
        new_password = input_validator.validate_password(request.new_password)

        service = DevoteeService(db)
        success = service.admin_reset_password(request.devotee_id, new_password, admin.id)

        if not success:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=AdminResetPasswordResponse(
                    success=False,
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="Admin password reset failed",
                    data=None,
                ).model_dump(),
            )

        logger.info(
            f"Admin {admin.id} ({admin.email}) reset password for devotee {request.devotee_id}"
        )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=AdminResetPasswordResponse(
                success=True,
                status_code=status.HTTP_200_OK,
                message="Password reset successful by admin",
                data={
                    "devotee_id": request.devotee_id,
                    "admin_id": admin.id,
                },
            ).model_dump(),
        )

    except HTTPException as e:
        # Convert HTTPException to standardized response
        logger.warning(f"Admin password reset failed: {e.detail}")
        return JSONResponse(
            status_code=e.status_code,
            content=AdminResetPasswordResponse(
                success=False,
                status_code=e.status_code,
                message=e.detail if isinstance(e.detail, str) else str(e.detail),
                data=None,
            ).model_dump(),
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error during admin password reset: {e!s}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=AdminResetPasswordResponse(
                success=False,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Database error occurred during admin password reset",
                data=None,
            ).model_dump(),
        )
    except Exception as e:
        logger.error(f"Unexpected error during admin password reset: {e!s}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=AdminResetPasswordResponse(
                success=False,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="An unexpected error occurred during admin password reset",
                data=None,
            ).model_dump(),
        )
