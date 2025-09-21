"""
Authentication API endpoints.

This module contains all authentication-related routes including signup, login,
and JWT token management.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    clear_reset_token,
    create_access_token,
    generate_password_reset_token,
    get_password_hash,
    is_token_expired,
    verify_password,
    verify_password_reset_token,
)
from app.db.models import User
from app.db.session import SessionLocal
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
from app.schemas.user import Token, UserLogin, UserSignup
from app.services.user_service import user_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def get_db():
    """Database dependency with robust error handling."""
    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError:
        logger.exception("Database error during request")
        try:
            db.rollback()
        except Exception:
            logger.exception("Failed to rollback transaction")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred",
        )
    finally:
        db.close()


@router.post(
    "/signup",
    response_model=SignupResponse,
    summary="User Registration with Email Verification",
)
async def signup(user_data: UserSignup, db: Session = Depends(get_db)):
    """
    Create a new user account requiring email verification.

    - **name**: User's full name (required)
    - **email**: Valid email address (required, must be unique)
    - **password**: Password with minimum 8 characters (required)
    - **chanting_rounds**: Daily chanting rounds 0-200 (optional, default 16)

    Creates an unverified account and sends a verification email.
    User must verify email before being able to login.
    """
    try:
        # Create unverified user (this will handle existing user checks)
        await user_service.create_unverified_user(db, user_data)

        logger.info(f"New unverified user registered: {user_data.email}")
        return SignupResponse(
            message="Account created successfully! Please check your email for verification link.",
            email=user_data.email,
            verification_required=True,
        )

    except HTTPException:
        # Re-raise known HTTP exceptions from user service
        raise
    except SQLAlchemyError:
        logger.exception("Database error during signup")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user account",
        )
    except Exception as e:
        logger.exception("Unexpected error during signup")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user account",
        ) from e


@router.post("/login", response_model=Token, summary="User Login")
def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate user and return JWT token.

    - **email**: User's email address (required)
    - **password**: User's password (required)

    Returns a JWT access token for API access.
    """
    try:
        # Find user by email
        user = (
            db.query(User).filter(User.email == user_credentials.email.lower()).first()
        )

        if not user or not verify_password(
            user_credentials.password, user.password_hash
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if email is verified
        if user.email_verified is False:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=(
                    "Please verify your email address before logging in. "
                    "Check your inbox or request a new verification email."
                ),
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create access token
        access_token = create_access_token(data={"sub": user.email})

        logger.info(f"User logged in: {user.email}")
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.jwt_access_token_expire_minutes * 60,
        }

    except HTTPException:
        raise
    except SQLAlchemyError:
        logger.exception("Error during login")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed",
        )


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    summary="Request Password Reset",
)
async def forgot_password(
    request_data: ForgotPasswordRequest, db: Session = Depends(get_db)
):
    """
    Request a password reset email.

    - **email**: Email address to send reset link to (required)

    Sends a secure password reset link to the user's email address.
    Always returns success to prevent email enumeration attacks.
    """
    try:
        from datetime import datetime, timedelta, timezone

        from app.services.email_service import email_service

        # Always return success to prevent email enumeration
        response = ForgotPasswordResponse(
            message="If this email is registered, you will receive a password reset link shortly.",
            email=request_data.email,
        )

        # Check if user exists (but don't reveal this information)
        user = db.query(User).filter(User.email == request_data.email.lower()).first()

        if user:
            # Generate reset token
            reset_token = generate_password_reset_token(user.email)

            # Store token and expiration in database
            user.password_reset_token = reset_token
            user.password_reset_expires = datetime.now(timezone.utc) + timedelta(
                hours=settings.password_reset_token_expire_hours
            )
            db.commit()

            # Send reset email
            try:
                await email_service.send_password_reset_email(
                    email=user.email,
                    reset_token=reset_token,
                    user_name=user.name,
                )
                logger.info(f"Password reset email sent to {user.email}")
            except Exception as e:
                logger.error(f"Failed to send password reset email: {e!s}")
                # Don't reveal email sending failure to user

        return response

    except SQLAlchemyError:
        logger.exception("Database error during forgot password")
        # Still return success to prevent enumeration
        return ForgotPasswordResponse(
            message="If this email is registered, you will receive a password reset link shortly.",
            email=request_data.email,
        )


@router.post(
    "/reset-password",
    response_model=ResetPasswordResponse,
    summary="Reset Password",
)
async def reset_password(
    request_data: ResetPasswordRequest, db: Session = Depends(get_db)
):
    """
    Reset password using the token from email.

    - **token**: Reset token from email (required)
    - **new_password**: New password meeting strength requirements (required)

    Resets the user's password and sends a confirmation email.
    """
    try:
        from app.services.email_service import email_service

        # Verify the reset token
        email = verify_password_reset_token(request_data.token)
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token",
            )

        # Find user by email
        user = db.query(User).filter(User.email == email.lower()).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token",
            )

        # Check if stored token matches and hasn't expired
        if (
            not user.password_reset_token
            or user.password_reset_token != request_data.token
            or is_token_expired(user)
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token",
            )

        # Update password
        user.password_hash = get_password_hash(request_data.new_password)

        # Clear reset token
        clear_reset_token(user, db)

        logger.info(f"Password reset successfully for user: {user.email}")

        # Send confirmation email (don't fail if this fails)
        try:
            await email_service.send_password_reset_confirmation(
                email=user.email, user_name=user.name
            )
        except Exception as e:
            logger.error(f"Failed to send confirmation email: {e!s}")

        return ResetPasswordResponse(
            message="Password has been reset successfully", email=user.email
        )

    except HTTPException:
        raise
    except SQLAlchemyError:
        logger.exception("Database error during password reset")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed",
        )


@router.post(
    "/verify-email",
    response_model=EmailVerificationResponse,
    summary="Verify Email Address",
)
async def verify_email(
    request_data: EmailVerificationRequest, db: Session = Depends(get_db)
):
    """
    Verify user's email address using verification token.

    - **token**: Verification token from email (required)

    Activates the user account and allows login.
    """
    try:
        # Verify the email with token
        user = await user_service.verify_email(db, request_data.token)

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification token",
            )

        logger.info(f"Email verified for user: {user.email}")
        return EmailVerificationResponse(
            message="Email verified successfully! You can now login to your account.",
            email=user.email,
            verified=True,
        )

    except HTTPException:
        # Re-raise known HTTP exceptions from user service
        raise
    except SQLAlchemyError:
        logger.exception("Database error during email verification")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email verification failed",
        )
    except Exception as e:
        logger.exception("Unexpected error during email verification")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email verification failed",
        ) from e


@router.post(
    "/resend-verification",
    response_model=ResendVerificationResponse,
    summary="Resend Email Verification",
)
async def resend_verification(
    request_data: ResendVerificationRequest, db: Session = Depends(get_db)
):
    """
    Resend email verification to user.

    - **email**: Email address to resend verification to (required)

    Sends a new verification email with a fresh token.
    Always returns success to prevent email enumeration attacks.
    """
    try:
        response = ResendVerificationResponse(
            message=(
                "If this email is registered and unverified, "
                "a new verification email has been sent."
            ),
            email=request_data.email,
        )

        # Find user by email (but don't reveal this information)
        user = db.query(User).filter(User.email == request_data.email.lower()).first()

        if user and user.email_verified is False:
            # Resend verification email
            try:
                await user_service.resend_verification_email(db, user)
                logger.info(f"Verification email resent to {user.email}")
            except Exception as e:
                logger.error(f"Failed to resend verification email: {e!r}")
                # Don't reveal email sending failure to user

        return response

    except SQLAlchemyError:
        logger.exception("Database error during resend verification")
        # Still return success to prevent enumeration
        return ResendVerificationResponse(
            message=(
                "If this email is registered and unverified, "
                "a new verification email has been sent."
            ),
            email=request_data.email,
        )
