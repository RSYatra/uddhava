"""
Devotee Authentication API endpoints.

This module contains all devotee authentication-related routes including signup,
login, email verification, password reset, and JWT token management.
"""

import logging
from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
    Request,
    status,
)
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.auth_decorators import admin_only_endpoint, get_current_user
from app.core.auth_security import (
    auth_security,
    error_handler,
    input_validator,
    token_manager,
)
from app.core.config import settings
from app.core.security import create_access_token
from app.db.models import Devotee
from app.db.session import SessionLocal
from app.schemas.auth import Token
from app.schemas.devotee import (
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
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
)
from app.services.devotee_service import DevoteeService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Devotee Authentication"])


def get_db():
    """Database dependency with robust error handling."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_devotee(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: Session = Depends(get_db),
):
    """
    Dependency to get the current authenticated devotee from JWT token.

    Args:
        credentials: HTTP Bearer authorization credentials
        db: Database session

    Returns:
        Current authenticated devotee

    Raises:
        HTTPException: If token is invalid or devotee not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Extract and verify token
        token = credentials.credentials
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])

        if payload is None:
            raise credentials_exception

        # For devotee tokens, 'sub' contains devotee.id and role should be 'devotee'
        devotee_id: str = payload.get("sub")
        role: str = payload.get("role")

        if devotee_id is None or role != "devotee":
            raise credentials_exception

        # Get devotee from database by ID
        devotee = db.query(Devotee).filter(Devotee.id == int(devotee_id)).first()
        if devotee is None:
            raise credentials_exception

        return devotee

    except (JWTError, ValueError):
        raise credentials_exception from None


@router.post(
    "/signup",
    response_model=SignupResponse,
    status_code=status.HTTP_200_OK,
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
        return SignupResponse(
            success=True,
            status_code=status.HTTP_200_OK,
            message="Registration successful. Verification email sent. Please check your inbox to verify your email address.",
            data={
                "user_id": devotee.id,
                "email": devotee.email,
                "email_verified": devotee.email_verified,
            },
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

        return SignupResponse(
            success=False,
            status_code=e.status_code,
            message=e.detail if isinstance(e.detail, str) else str(e.detail),
            data=response_data,
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error during devotee signup: {e!s}")
        return SignupResponse(
            success=False,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Database error occurred during registration",
            data=None,
        )
    except Exception as e:
        logger.error(f"Unexpected error during devotee signup: {e!s}")
        return SignupResponse(
            success=False,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="An unexpected error occurred during registration",
            data=None,
        )


@router.post("/complete-profile", response_model=dict[str, str])
async def complete_devotee_profile(
    # Required fields for profile completion
    date_of_birth: str = Form(...),  # Will be parsed to date
    gender: str = Form(...),
    marital_status: str = Form(...),
    country_code: str = Form(...),
    mobile_number: str = Form(...),
    father_name: str = Form(...),
    mother_name: str = Form(...),
    # Optional fields
    spouse_name: str = Form(None),
    date_of_marriage: str = Form(None),
    national_id: str = Form(None),
    address: str = Form(None),
    city: str = Form(None),
    state_province: str = Form(None),
    country: str = Form(None),
    postal_code: str = Form(None),
    # Spiritual fields
    initiation_status: str = Form(None),
    spiritual_master: str = Form(None),
    initiation_date: str = Form(None),
    initiation_place: str = Form(None),
    spiritual_guide: str = Form(None),
    # ISKCON Journey
    when_were_you_introduced_to_iskcon: str = Form(None),
    who_introduced_you_to_iskcon: str = Form(None),
    which_iskcon_center_you_first_connected_to: str = Form(None),
    # Chanting
    chanting_number_of_rounds: int = Form(16),
    chanting_16_rounds_since: str = Form(None),
    # Education
    devotional_courses: str = Form(None),
    # Authentication and database dependencies
    current_devotee: Devotee = Depends(get_current_devotee),
    db: Session = Depends(get_db),
):
    """
    Complete devotee profile after initial signup and email verification.

    This endpoint allows verified devotees to add detailed information
    to their profile including personal, family, spiritual, and location details.

    **Security Features:**
    - Requires authenticated user (current_user dependency)
    - Input validation and sanitization for all fields
    - File upload security checks for photos
    - Users can only complete their own profile
    """
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

        # Complete the profile using the authenticated user's ID
        success = await service.complete_devotee_profile(user_id, profile_data)

        if success:
            logger.info(f"Profile completed successfully for user {user_id}")
            return {
                "message": "Profile completed successfully",
                "status": "success",
            }
        logger.warning(f"Failed to complete profile for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to complete profile. Please check your data and try again.",
        )

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error during profile completion: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred during profile completion",
        ) from None
    except Exception as e:
        logger.error(f"Unexpected error during profile completion: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during profile completion",
        ) from None


@router.post("/login", response_model=Token)
async def devotee_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    Login devotee with email and password.

    Returns JWT access token for authenticated devotee.
    Devotee must have verified email to login.

    Security Features:
    - Rate limiting to prevent brute force attacks
    - Email validation and normalization
    - Secure error messages (no information leakage)
    - Failed attempt tracking
    - IP blocking for suspicious activity
    """
    try:
        # Validate and sanitize email
        email = input_validator.validate_email(email)

        # Apply rate limiting before authentication attempt
        auth_security.check_login_rate_limit(request, email)

        service = DevoteeService(db)

        devotee = service.authenticate_devotee(email, password)
        if not devotee:
            # Use generic error message to prevent email enumeration
            logger.warning(f"Failed login attempt for email: {email}")
            raise error_handler.safe_error_response("auth_failed")

        # Clear rate limiting on successful login
        auth_security.record_successful_login(request, email)

        access_token = create_access_token(
            data={
                "sub": str(devotee.id),
                "email": devotee.email,
                "role": "devotee",
            }
        )

        logger.info(f"Devotee login successful for email: {email}")
        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.jwt_access_token_expire_minutes * 60,
        )  # nosec B106

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error during devotee login: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred during login",
        ) from None
    except Exception as e:
        logger.error(f"Unexpected error during devotee login: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during login",
        ) from None


@router.post("/verify-email", response_model=EmailVerificationResponse)
async def verify_devotee_email(request: EmailVerificationRequest, db: Session = Depends(get_db)):
    """
    Verify devotee's email address using verification token.

    This endpoint is called when devotee clicks the verification link in their email.
    Upon successful verification, the devotee can login to their account.

    Security Features:
    - Token format validation
    - Secure error handling
    - Token expiration checks
    - Prevention of token reuse
    """
    try:
        logger.info(f"Starting email verification for token: {request.token[:8]}...")

        # Validate token format to prevent injection attacks
        if not token_manager.validate_token_format(request.token):
            logger.warning("Token format validation failed")
            raise error_handler.safe_error_response("token_invalid")

        service = DevoteeService(db)
        verified_email = await service.verify_devotee_email(request.token)

        logger.info(f"Devotee email verification successful for token: {request.token[:8]}...")
        return EmailVerificationResponse(
            message="Email verified successfully. You can now login to your account.",
            email=verified_email,
            verified=True,
        )

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error during devotee email verification: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred during email verification",
        ) from None
    except Exception as e:
        logger.error(f"Unexpected error during devotee email verification: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during email verification",
        ) from None


@router.post("/resend-verification", response_model=ResendVerificationResponse)
async def resend_devotee_verification(
    request: ResendVerificationRequest, db: Session = Depends(get_db)
):
    """
    Resend email verification to devotee.

    This endpoint can be used if the devotee didn't receive the initial
    verification email or if the verification token has expired.
    """
    try:
        service = DevoteeService(db)

        success = await service.resend_verification_email(request.email)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to resend verification email",
            )

        logger.info(f"Devotee verification email resent to: {request.email}")
        return ResendVerificationResponse(
            message="Verification email sent. Please check your inbox and spam folder.",
            email_sent=True,
        )

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error during devotee resend verification: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while resending verification email",
        ) from None
    except Exception as e:
        logger.error(f"Unexpected error during devotee resend verification: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while resending verification email",
        ) from None


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def devotee_forgot_password(
    request_obj: Request,
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    """
    Send password reset email to devotee.

    If the email exists and is verified, sends a password reset email.
    For security, always returns success even if email doesn't exist.

    Security Features:
    - Rate limiting to prevent email enumeration attacks
    - Email validation and normalization
    - Generic responses to prevent information disclosure
    - Request tracking and suspicious activity detection
    """
    try:
        # Validate and sanitize email
        email = input_validator.validate_email(request.email)

        # Apply rate limiting for password reset requests
        auth_security.check_password_reset_rate_limit(request_obj, email)

        service = DevoteeService(db)

        await service.send_password_reset_email(email)

        logger.info(f"Password reset email sent to: {email}")
        return ForgotPasswordResponse(
            message=(
                "If this email is registered and verified, "
                "you will receive password reset instructions."
            ),
            email_sent=True,
        )

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error during devotee forgot password: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while sending password reset email",
        ) from None
    except Exception as e:
        logger.error(f"Unexpected error during devotee forgot password: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while sending password reset email",
        ) from None


@router.post("/reset-password", response_model=ResetPasswordResponse)
async def devotee_reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Reset devotee's password using reset token.

    This endpoint is called when devotee submits the password reset form
    after clicking the reset link in their email.

    Security Features:
    - Token format validation
    - Password strength validation
    - Token expiration checks
    - Secure error handling
    - One-time token usage
    """
    try:
        # Validate token format
        if not token_manager.validate_token_format(request.token):
            raise error_handler.safe_error_response("token_invalid")

        # Validate new password strength
        new_password = input_validator.validate_password(request.new_password)

        service = DevoteeService(db)

        success = service.reset_password_with_token(request.token, new_password)
        if not success:
            raise error_handler.safe_error_response("token_invalid")

        logger.info(f"Password reset successful for token: {request.token[:8]}...")
        return ResetPasswordResponse(
            message="Password reset successful. You can now login with your new password.",
            reset_successful=True,
        )

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error during devotee password reset: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred during password reset",
        ) from None
    except Exception as e:
        logger.error(f"Unexpected error during devotee password reset: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during password reset",
        ) from None


@router.post("/admin/reset-password")
@admin_only_endpoint
async def admin_reset_devotee_password(
    devotee_id: int,
    new_password: str,
    db: Session = Depends(get_db),
    current_user: Devotee = Depends(get_current_user),
) -> dict[str, str]:
    """
    Admin endpoint to reset any devotee's password.

    This is for administrative purposes when devotees need password assistance.
    Requires admin authentication.
    """
    try:
        service = DevoteeService(db)

        success = service.admin_reset_password(devotee_id, new_password, current_user.id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admin password reset failed",
            )

        logger.info(
            f"Admin {current_user.id} ({current_user.email}) "
            f"reset password for devotee {devotee_id}"
        )
        return {
            "message": "Password reset successful",
            "devotee_id": str(devotee_id),
        }

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error during admin password reset: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred during admin password reset",
        ) from None
    except Exception as e:
        logger.error(f"Unexpected error during admin password reset: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during admin password reset",
        ) from None
