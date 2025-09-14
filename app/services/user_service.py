"""
User business logic service.

This service encapsulates user-related business logic,
keeping it separate from HTTP/API concerns.
"""

import logging
from pathlib import Path
from typing import List, Optional

from fastapi import HTTPException, UploadFile, status
from pydantic import EmailStr
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.models import User
from app.schemas.user import UserCreate, UserUpdate

logger = logging.getLogger(__name__)


class UserService:
    """Service class for user business logic."""

    def __init__(self):
        self.upload_dir = Path(settings.upload_directory)
        self.upload_dir.mkdir(exist_ok=True)

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
