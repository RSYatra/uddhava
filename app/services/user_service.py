"""
User business logic service.

This service encapsulates user-related business logic,
keeping it separate from HTTP/API concerns.
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import HTTPException, UploadFile, status
from pydantic import EmailStr
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.models import User
from app.schemas.user import UserCreate, UserUpdate
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)


class UserService:
    """Service class for user business logic."""

    def __init__(self):
        self.upload_dir = Path(settings.upload_directory)
        self.upload_dir.mkdir(exist_ok=True)
        self.email_service = EmailService()

    def create_user(
        self,
        db: Session,
        user_data: UserCreate,
        photo: Optional[UploadFile] = None,
    ) -> User:
        """
        Create a new user with optional photo.

        Args:
            db: Database session
            user_data: User creation data
            photo: Optional photo file

        Returns:
            Created User instance

        Raises:
            HTTPException: If user already exists or validation fails
        """
        # Check if user exists
        existing_user = (
            db.query(User).filter(User.email == user_data.email.lower()).first()
        )
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists",
            )

        # Handle photo upload
        photo_path = None
        if photo:
            photo_path = self._save_photo(photo, user_data.email)

        # Create user
        db_user = User(
            name=user_data.name,
            email=user_data.email.lower(),
            password_hash=get_password_hash(user_data.password),
            chanting_rounds=user_data.chanting_rounds,
            photo_path=photo_path,
        )

        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        logger.info(f"Created user: {db_user.email}")
        return db_user

    def get_users(self, db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        """Get paginated list of users."""
        return db.query(User).offset(skip).limit(limit).all()

    def get_user_by_id(self, db: Session, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return db.query(User).filter(User.id == user_id).first()

    def get_user_by_email(self, db: Session, email: EmailStr) -> Optional[User]:
        """Get user by email."""
        return db.query(User).filter(User.email == email.lower()).first()

    def update_user(
        self,
        db: Session,
        user_id: int,
        user_update: UserUpdate,
        photo: Optional[UploadFile] = None,
    ) -> Optional[User]:
        """
        Update user information.

        Args:
            db: Database session
            user_id: User ID to update
            user_update: Update data
            photo: Optional new photo

        Returns:
            Updated User or None if not found
        """
        user = self.get_user_by_id(db, user_id)
        if not user:
            return None

        # Update fields
        update_data = user_update.model_dump(exclude_unset=True)
        if "password" in update_data:
            update_data["password_hash"] = get_password_hash(
                update_data.pop("password")
            )

        # Handle photo upload
        if photo:
            # Remove old photo if exists
            if user.photo_path:
                old_photo = self.upload_dir / user.photo_path
                if old_photo.exists():
                    old_photo.unlink()

            # Save new photo
            update_data["photo_path"] = self._save_photo(photo, user.email)

        # Apply updates
        for field, value in update_data.items():
            setattr(user, field, value)

        db.commit()
        db.refresh(user)

        logger.info(f"Updated user: {user.email}")
        return user

    async def create_unverified_user(
        self,
        db: Session,
        user_data: UserCreate,
        photo: Optional[UploadFile] = None,
    ) -> User:
        """
        Create a new unverified user and send verification email.

        Args:
            db: Database session
            user_data: User creation data
            photo: Optional photo file

        Returns:
            Created User instance (unverified)

        Raises:
            HTTPException: If user already exists or validation fails
        """
        # Check if user exists
        existing_user = (
            db.query(User).filter(User.email == user_data.email.lower()).first()
        )
        if existing_user:
            if existing_user.email_verified is True:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this email already exists and is verified",
                )
            # User exists but not verified, resend verification email
            await self.resend_verification_email(db, existing_user)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "User with this email already exists. "
                    "Please check your email for verification link or request a new one."
                ),
            )

        # Handle photo upload
        photo_path = None
        if photo:
            photo_path = self._save_photo(photo, user_data.email)

        # Generate verification token
        verification_token = self._generate_verification_token()
        verification_expires = datetime.now(timezone.utc) + timedelta(
            hours=settings.email_verification_token_expire_hours
        )

        # Create unverified user
        db_user = User(
            name=user_data.name,
            email=user_data.email.lower(),
            password_hash=get_password_hash(user_data.password),
            chanting_rounds=user_data.chanting_rounds,
            photo_path=photo_path,
            email_verified=False,  # Set to False initially
            verification_token=verification_token,
            verification_expires=verification_expires,
        )

        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        # Send verification email
        await self.email_service.send_email_verification(
            email=db_user.email,
            verification_token=verification_token,
            user_name=db_user.name,
        )

        logger.info(f"Created unverified user: {db_user.email}")
        return db_user

    async def verify_email(
        self, db: Session, verification_token: str
    ) -> Optional[User]:
        """
        Verify user email with token.

        Args:
            db: Database session
            verification_token: Token from email verification link

        Returns:
            Verified User or None if token is invalid/expired

        Raises:
            HTTPException: If token is invalid, expired, or already used
        """
        # Find user by verification token
        user = (
            db.query(User).filter(User.verification_token == verification_token).first()
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification token",
            )

        if user.email_verified is True:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already verified",
            )

        # Check if token is expired
        current_time = datetime.now(timezone.utc)
        expires_at = getattr(user, "verification_expires", None)
        if expires_at is not None and expires_at < current_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification token has expired. Please request a new one.",
            )

        # Mark as verified
        user.email_verified = True
        user.verification_token = None
        user.verification_expires = None

        db.commit()
        db.refresh(user)

        # Send success confirmation email
        await self.email_service.send_email_verification_success(
            email=user.email, user_name=user.name
        )

        logger.info(f"Email verified for user: {user.email}")
        return user

    async def resend_verification_email(self, db: Session, user: User) -> bool:
        """
        Resend verification email to user.

        Args:
            db: Database session
            user: User to resend verification to

        Returns:
            bool: True if email was sent successfully

        Raises:
            HTTPException: If user is already verified or other errors
        """
        if user.email_verified is True:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already verified",
            )

        # Generate new verification token
        verification_token = self._generate_verification_token()
        verification_expires = datetime.now(timezone.utc) + timedelta(
            hours=settings.email_verification_token_expire_hours
        )

        # Update user with new token
        user.verification_token = verification_token
        user.verification_expires = verification_expires

        db.commit()

        # Send verification email
        await self.email_service.send_email_verification(
            email=user.email,
            verification_token=verification_token,
            user_name=user.name,
        )

        logger.info(f"Resent verification email to: {user.email}")
        return True

    def get_user_by_verification_token(
        self, db: Session, verification_token: str
    ) -> Optional[User]:
        """Get user by verification token."""
        return (
            db.query(User).filter(User.verification_token == verification_token).first()
        )

    def _generate_verification_token(self) -> str:
        """Generate a secure verification token."""
        return secrets.token_urlsafe(32)

    def _save_photo(self, photo: UploadFile, user_email: str) -> str:
        """Save uploaded photo and return relative path."""
        # Validate file
        if not photo.content_type or not photo.content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only image files are allowed",
            )

        # Generate filename
        file_extension = photo.filename.split(".")[-1].lower()
        safe_email = user_email.replace("@", "_at_").replace(".", "_")
        filename = f"user_{safe_email}.{file_extension}"
        file_path = self.upload_dir / filename

        # Save file
        try:
            with open(file_path, "wb") as buffer:
                content = photo.file.read()
                buffer.write(content)

            logger.info(f"Saved photo: {filename}")
            return filename

        except Exception as e:
            logger.error(f"Failed to save photo: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save photo",
            )


# Global service instance
user_service = UserService()
