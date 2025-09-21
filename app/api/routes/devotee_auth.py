"""
Devotee Authentication API endpoints.

This module contains all devotee authentication-related routes including signup,
login, email verification, password reset, and JWT token management.
"""

import logging
from datetime import datetime
from typing import Dict

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
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.auth_decorators import admin_only_endpoint, get_current_user
from app.core.auth_security import (
    auth_security,
    error_handler,
    input_validator,
    token_manager,
)
from app.core.security import create_access_token
from app.db.models import User
from app.db.session import SessionLocal
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
from app.schemas.user import Token
from app.services.devotee_service import DevoteeService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/devotees/auth", tags=["Devotee Authentication"])


def get_db():
    """Database dependency with robust error handling."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/signup", response_model=SignupResponse)
async def devotee_signup(
    request: Request,
    devotee_data: DevoteeSimpleCreate,
    db: Session = Depends(get_db),
):
    """
    Register a new devotee with simplified signup process.

    Creates an unverified devotee account with minimal information and sends
    verification email. After verification, devotees can complete their profile.

    Security Features:
    - Rate limiting to prevent spam signups
    - Input validation and sanitization
    - Password strength requirements
    - Email format validation
    """
    try:
        # Apply rate limiting
        auth_security.check_signup_rate_limit(request)

        # Validate and sanitize inputs from the incoming data
        email = input_validator.validate_email(devotee_data.email)
        password = input_validator.validate_password(devotee_data.password)
        name = input_validator.sanitize_string(devotee_data.name, 127)

        # Create validated devotee data
        validated_devotee_data = DevoteeSimpleCreate(
            name=name,
            email=email,
            password=password,
        )

        service = DevoteeService()
        devotee = await service.create_simple_unverified_devotee(
            db, validated_devotee_data
        )

        logger.info(f"Simplified devotee signup successful for email: {email}")
        return SignupResponse(
            message=(
                "Registration successful! Please check your email for verification instructions. "
                "After verification, you can complete your profile."
            ),
            email=devotee.email,
        )

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error during devotee signup: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred during registration",
        ) from None
    except Exception as e:
        logger.error(f"Unexpected error during devotee signup: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during registration",
        ) from None


@router.post("/complete-profile", response_model=Dict[str, str])
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
    # Photo upload
    photo: UploadFile = File(None),
    # Authentication and database dependencies
    current_user: User = Depends(get_current_user),
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
        # Get the authenticated user's ID
        user_id = current_user.id

        # Validate and sanitize inputs
        father_name = input_validator.sanitize_string(father_name, 127)
        mother_name = input_validator.sanitize_string(mother_name, 127)

        # Validate phone number
        mobile_number = input_validator.validate_phone_number(mobile_number)

        # Sanitize optional fields
        spouse_name = (
            input_validator.sanitize_string(spouse_name or "", 127)
            if spouse_name
            else None
        )
        national_id = (
            input_validator.sanitize_string(national_id or "", 50)
            if national_id
            else None
        )
        address = (
            input_validator.sanitize_string(address or "", 255) if address else None
        )
        city = input_validator.sanitize_string(city or "", 100) if city else None
        state_province = (
            input_validator.sanitize_string(state_province or "", 100)
            if state_province
            else None
        )
        country = (
            input_validator.sanitize_string(country or "", 100) if country else None
        )
        postal_code = (
            input_validator.sanitize_string(postal_code or "", 20)
            if postal_code
            else None
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
            input_validator.sanitize_string(spiritual_guide or "", 127)
            if spiritual_guide
            else None
        )
        who_introduced_you_to_iskcon = (
            input_validator.sanitize_string(who_introduced_you_to_iskcon or "", 127)
            if who_introduced_you_to_iskcon
            else None
        )
        which_iskcon_center_you_first_connected_to = (
            input_validator.sanitize_string(
                which_iskcon_center_you_first_connected_to or "", 127
            )
            if which_iskcon_center_you_first_connected_to
            else None
        )
        when_were_you_introduced_to_iskcon = (
            input_validator.sanitize_string(
                when_were_you_introduced_to_iskcon or "", 127
            )
            if when_were_you_introduced_to_iskcon
            else None
        )

        # Validate chanting rounds (using constant for max rounds)
        MAX_CHANTING_ROUNDS = 200
        if (
            chanting_number_of_rounds < 0
            or chanting_number_of_rounds > MAX_CHANTING_ROUNDS
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Chanting rounds must be between 0 and {MAX_CHANTING_ROUNDS}",
            )

        # Parse dates
        parsed_date_of_birth = (
            datetime.strptime(date_of_birth, "%Y-%m-%d").date()
            if date_of_birth
            else None
        )
        parsed_date_of_marriage = (
            datetime.strptime(date_of_marriage, "%Y-%m-%d").date()
            if date_of_marriage
            else None
        )
        parsed_initiation_date = (
            datetime.strptime(initiation_date, "%Y-%m-%d").date()
            if initiation_date
            else None
        )
        parsed_introduced_date = (
            datetime.strptime(when_were_you_introduced_to_iskcon, "%Y-%m-%d").date()
            if when_were_you_introduced_to_iskcon
            else None
        )
        parsed_chanting_since = (
            datetime.strptime(chanting_16_rounds_since, "%Y-%m-%d").date()
            if chanting_16_rounds_since
            else None
        )

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
        success = await service.complete_devotee_profile(user_id, profile_data, photo)

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
        return Token(access_token=access_token, token_type="bearer")  # nosec B106

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
async def verify_devotee_email(
    request: EmailVerificationRequest, db: Session = Depends(get_db)
):
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
        # Validate token format to prevent injection attacks
        if not token_manager.validate_token_format(request.token):
            raise error_handler.safe_error_response("token_invalid")

        service = DevoteeService(db)

        success = await service.verify_devotee_email(request.token)
        if not success:
            raise error_handler.safe_error_response("token_invalid")

        logger.info(
            f"Devotee email verification successful for token: {request.token[:8]}..."
        )
        return EmailVerificationResponse(
            message="Email verified successfully. You can now login to your account.",
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
async def devotee_reset_password(
    request: ResetPasswordRequest, db: Session = Depends(get_db)
):
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
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    """
    Admin endpoint to reset any devotee's password.

    This is for administrative purposes when devotees need password assistance.
    Requires admin authentication.
    """
    try:
        service = DevoteeService(db)

        success = service.admin_reset_password(
            devotee_id, new_password, current_user.id
        )
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
