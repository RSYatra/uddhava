"""
Authentication API endpoints.

Simple and clean authentication for signup, login, email verification, and password reset.
"""

import logging
from datetime import datetime, timedelta
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.db.models import Devotee
from app.db.session import get_db
from app.core.security import create_access_token, get_password_hash, verify_password
from app.core.config import settings
from app.services.smtp_service import SMTPService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ============================================================================
# REQUEST/RESPONSE SCHEMAS
# ============================================================================

class SignupRequest(BaseModel):
    """Signup request schema."""

    legal_name: str = Field(..., min_length=1, max_length=127, description="Full name")
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=8, max_length=128, description="Password")

    class Config:
        json_schema_extra = {
            "example": {
                "legal_name": "Radha Krishna",
                "email": "user@example.com",
                "password": "SecurePass123!",
            }
        }


class LoginRequest(BaseModel):
    """Login request schema."""

    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., description="Password")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123!",
            }
        }


class LoginResponse(BaseModel):
    """Login response schema."""

    success: bool
    message: str
    data: dict | None = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Login successful",
                "data": {
                    "access_token": "eyJhbGc...",
                    "token_type": "bearer",
                    "user": {
                        "id": 1,
                        "email": "user@example.com",
                        "legal_name": "Radha Krishna",
                    },
                },
            }
        }


class ForgotPasswordRequest(BaseModel):
    """Forgot password request schema."""

    email: EmailStr = Field(..., description="Email address")

    class Config:
        json_schema_extra = {"example": {"email": "user@example.com"}}


class ResetPasswordRequest(BaseModel):
    """Reset password request schema."""

    token: str = Field(..., description="Password reset token from email")
    password: str = Field(..., min_length=8, max_length=128, description="New password")

    class Config:
        json_schema_extra = {
            "example": {
                "token": "token_from_email",
                "password": "NewSecurePass123!",
            }
        }


class VerifyEmailRequest(BaseModel):
    """Email verification request schema."""

    token: str = Field(..., description="Email verification token from email")

    class Config:
        json_schema_extra = {"example": {"token": "token_from_email"}}


class GenericResponse(BaseModel):
    """Generic response schema."""

    success: bool
    message: str
    data: dict | None = None


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def _generate_secure_token() -> str:
    """Generate a secure random token."""
    return secrets.token_urlsafe(32)


def _validate_password_strength(password: str) -> tuple[bool, str | None]:
    """
    Validate password strength.
    
    Returns: (is_valid, error_message)
    """
    if len(password) < 8 or len(password) > 128:
        return False, "Password must be 8-128 characters"

    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

    if not (has_upper and has_lower and has_digit and has_special):
        return (
            False,
            "Password must contain uppercase, lowercase, digit, and special character",
        )

    return True, None


# ============================================================================
# SIGNUP ENDPOINT
# ============================================================================


@router.post("/signup", response_model=GenericResponse, status_code=status.HTTP_200_OK)
async def signup(
    request: Request,
    signup_data: SignupRequest,
    db: Session = Depends(get_db),
) -> dict:
    """
    Register a new user account.

    - Validates password strength
    - Sends verification email
    - Account is unverified until email is confirmed
    """
    try:
        # Normalize email
        email = signup_data.email.strip().lower()
        legal_name = signup_data.legal_name.strip()
        password = signup_data.password.strip()

        # Validate password strength
        is_valid, error_msg = _validate_password_strength(password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg,
            )

        # Check if user already exists
        existing_user = db.query(Devotee).filter(Devotee.email == email).first()
        if existing_user:
            if existing_user.email_verified:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email already registered. Please login instead.",
                )
            else:
                # Resend verification email
                try:
                    verification_token = existing_user.verification_token or _generate_secure_token()
                    smtp = SMTPService()
                    await smtp.send_verification_email(
                        to_email=email,
                        user_name=existing_user.legal_name,
                        verification_token=verification_token,
                    )
                except Exception as e:
                    logger.error(f"Failed to resend verification email: {e}")

                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email registered but not verified. Verification email sent.",
                )

        # Create new user
        verification_token = _generate_secure_token()
        password_hash = get_password_hash(password)

        devotee = Devotee(
            email=email,
            legal_name=legal_name,
            password_hash=password_hash,
            email_verified=False,
            verification_token=verification_token,
            verification_expires=datetime.utcnow() + timedelta(hours=24),
            role="USER",
        )

        db.add(devotee)
        db.commit()
        db.refresh(devotee)

        # Send verification email
        try:
            smtp = SMTPService()
            await smtp.send_verification_email(
                to_email=email,
                user_name=legal_name,
                verification_token=verification_token,
            )
        except Exception as e:
            logger.error(f"Failed to send verification email: {e}")
            # Don't fail the signup if email fails, but log it
            db.delete(devotee)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send verification email. Please try again.",
            )

        logger.info(f"User signup successful: {email}")
        return {
            "success": True,
            "message": "Registration successful. Please check your email to verify your account.",
            "data": {
                "user_id": devotee.id,
                "email": devotee.email,
            },
        }

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error during signup: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error. Please try again later.",
        )
    except Exception as e:
        logger.error(f"Unexpected error during signup: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again.",
        )


# ============================================================================
# EMAIL VERIFICATION ENDPOINT
# ============================================================================


@router.post("/verify-email", response_model=GenericResponse, status_code=status.HTTP_200_OK)
async def verify_email(
    verify_data: VerifyEmailRequest,
    db: Session = Depends(get_db),
) -> dict:
    """
    Verify email address using token from verification email.
    """
    try:
        token = verify_data.token.strip()

        devotee = (
            db.query(Devotee)
            .filter(Devotee.verification_token == token)
            .first()
        )

        if not devotee:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token.",
            )

        if devotee.email_verified:
            return {
                "success": True,
                "message": "Email already verified.",
                "data": None,
            }

        if devotee.verification_expires and devotee.verification_expires < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification token has expired. Please request a new one.",
            )

        # Mark email as verified
        devotee.email_verified = True
        devotee.verification_token = None
        devotee.verification_expires = None
        db.add(devotee)
        db.commit()

        logger.info(f"Email verified: {devotee.email}")
        return {
            "success": True,
            "message": "Email verified successfully. You can now login.",
            "data": None,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during verification.",
        )


# ============================================================================
# LOGIN ENDPOINT
# ============================================================================


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db),
) -> dict:
    """
    Login with email and password.

    Returns JWT access token on success.
    """
    try:
        email = login_data.email.strip().lower()
        password = login_data.password.strip()

        devotee = db.query(Devotee).filter(Devotee.email == email).first()

        if not devotee or not verify_password(password, devotee.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        if not devotee.email_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email not verified. Please check your email for verification link.",
            )

        # Generate JWT token
        access_token = create_access_token(
            data={"sub": str(devotee.id), "email": devotee.email}
        )

        logger.info(f"User login successful: {email}")
        return {
            "success": True,
            "message": "Login successful.",
            "data": {
                "access_token": access_token,
                "token_type": "bearer",
                "user": {
                    "id": devotee.id,
                    "email": devotee.email,
                    "legal_name": devotee.legal_name,
                },
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login.",
        )


# ============================================================================
# FORGOT PASSWORD ENDPOINT
# ============================================================================


@router.post("/forgot-password", response_model=GenericResponse, status_code=status.HTTP_200_OK)
async def forgot_password(
    forgot_data: ForgotPasswordRequest,
    db: Session = Depends(get_db),
) -> dict:
    """
    Request password reset email.

    Returns success regardless of email existence (security).
    """
    try:
        email = forgot_data.email.strip().lower()

        devotee = db.query(Devotee).filter(Devotee.email == email).first()

        if devotee:
            # Generate reset token
            reset_token = _generate_secure_token()
            devotee.password_reset_token = reset_token
            devotee.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
            db.add(devotee)
            db.commit()

            # Send reset email
            try:
                smtp = SMTPService()
                await smtp.send_password_reset_email(
                    to_email=email,
                    user_name=devotee.legal_name,
                    reset_token=reset_token,
                )
            except Exception as e:
                logger.error(f"Failed to send password reset email: {e}")

        # Always return success for security (don't reveal if email exists)
        logger.info(f"Password reset requested for: {email}")
        return {
            "success": True,
            "message": "If an account exists with this email, a password reset link has been sent.",
            "data": None,
        }

    except Exception as e:
        logger.error(f"Error during forgot password: {e}")
        # Still return success for security
        return {
            "success": True,
            "message": "If an account exists with this email, a password reset link has been sent.",
            "data": None,
        }


# ============================================================================
# RESET PASSWORD ENDPOINT
# ============================================================================


@router.post("/reset-password", response_model=GenericResponse, status_code=status.HTTP_200_OK)
async def reset_password(
    reset_data: ResetPasswordRequest,
    db: Session = Depends(get_db),
) -> dict:
    """
    Reset password using token from reset email.
    """
    try:
        token = reset_data.token.strip()
        password = reset_data.password.strip()

        # Validate password strength
        is_valid, error_msg = _validate_password_strength(password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg,
            )

        devotee = (
            db.query(Devotee)
            .filter(Devotee.password_reset_token == token)
            .first()
        )

        if not devotee:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token.",
            )

        if devotee.password_reset_expires and devotee.password_reset_expires < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token has expired. Please request a new one.",
            )

        # Update password
        devotee.password_hash = get_password_hash(password)
        devotee.password_reset_token = None
        devotee.password_reset_expires = None
        db.add(devotee)
        db.commit()

        logger.info(f"Password reset successful: {devotee.email}")
        return {
            "success": True,
            "message": "Password reset successful. You can now login with your new password.",
            "data": None,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during password reset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during password reset.",
        )
