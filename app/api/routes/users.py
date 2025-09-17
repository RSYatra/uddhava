"""
User management API endpoints.

This module contains all user-related routes including CRUD operations,
profile management, and user listings.
"""

import logging
import shutil
import time
from pathlib import Path
from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from pydantic import EmailStr, ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.auth_decorators import (
    admin_only_endpoint,
    owner_or_admin_endpoint,
)
from app.core.config import settings
from app.core.security import get_current_user, get_password_hash
from app.db.models import User
from app.db.session import SessionLocal
from app.schemas.user import UserOut, UserUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])

# File upload constants
UPLOAD_DIR = Path(settings.upload_directory)
UPLOAD_DIR.mkdir(exist_ok=True)
MAX_FILE_SIZE = settings.max_upload_size_bytes
ALLOWED_EXTENSIONS = settings.allowed_extensions


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


@router.get("/", response_model=List[UserOut], summary="List Users (Admin Only)")
@admin_only_endpoint
async def get_users(
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve a list of users with pagination (Admin only).

    - **limit**: Maximum number of users to return (default: 100)
    - **offset**: Number of users to skip (default: 0)

    Returns a list of user objects with public information only.

    SECURITY: This endpoint requires admin authentication.
    """
    try:
        users = db.query(User).offset(offset).limit(limit).all()
        logger.info(f"Admin {current_user.email} retrieved {len(users)} users")
        return users
    except SQLAlchemyError:
        logger.exception("Error retrieving users")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users",
        )


@router.post("/", response_model=UserOut, summary="Create User (Admin)")
@admin_only_endpoint
async def create_user(
    name: str = Form(..., min_length=1, max_length=255),
    email: str = Form(..., max_length=255),
    password: str = Form(..., min_length=8, max_length=128),
    chanting_rounds: int = Form(..., ge=0, le=200),
    photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new user with optional photo upload (Admin endpoint).

    This is different from signup - it's for admin user creation.

    - **name**: User's full name (required)
    - **email**: Valid email address (required, must be unique)
    - **password**: Password with minimum 8 characters (required)
    - **chanting_rounds**: Daily chanting rounds 0-200 (optional, default 16)
    - **photo**: Optional profile photo file

    SECURITY: This endpoint requires authentication. Currently limited to
    authenticated users, but should be restricted to admin users only
    when role system is implemented.
    """
    try:
        logger.info(f"Admin {current_user.email} creating new user: {email}")

        # Validate email format using Pydantic model
        from pydantic import BaseModel

        class EmailValidator(BaseModel):
            email: EmailStr

        try:
            validator = EmailValidator(email=email.lower().strip())
            validated_email = validator.email
        except ValidationError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format",
            )

        # Check if email exists
        existing_user = db.query(User).filter(User.email == validated_email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        photo_path = None
        if photo and photo.filename:
            # Validate file size - handle case where size might be None
            file_size = getattr(photo, "size", None)
            if file_size is not None and file_size > MAX_FILE_SIZE:
                size_limit_mb = MAX_FILE_SIZE // (1024 * 1024)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File size exceeds {size_limit_mb}MB limit",
                )

            # Validate file type
            file_extension = Path(photo.filename).suffix.lower()
            if file_extension not in ALLOWED_EXTENSIONS:
                allowed = ", ".join(ALLOWED_EXTENSIONS)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid file type. Allowed: {allowed}",
                )

            # Save file with timestamp to prevent race conditions
            timestamp = str(int(time.time() * 1000))  # millisecond timestamp
            safe_filename = f"{validated_email}_{timestamp}_{photo.filename}"
            photo_path = UPLOAD_DIR / safe_filename

            try:
                with open(photo_path, "wb") as buffer:
                    shutil.copyfileobj(photo.file, buffer)
                logger.info(f"Photo saved: {photo_path}")
            except Exception as e:
                logger.error(f"Failed to save photo: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to save uploaded file",
                )

        # Create user
        hashed_pwd = get_password_hash(password)  # Not a hardcoded password
        user = User(
            name=name.strip(),
            email=validated_email,
            password_hash=hashed_pwd,
            chanting_rounds=chanting_rounds,
            photo=str(photo_path) if photo_path else None,
        )

        try:
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"User created: {user.email}")
            return user
        except IntegrityError:
            logger.warning(
                "IntegrityError on user create (likely duplicate) %s",
                validated_email,
            )
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
        except Exception as db_error:
            # If user creation fails and we saved a file, clean it up
            if photo_path and photo_path.exists():
                try:
                    photo_path.unlink()
                    logger.info(f"Cleaned up failed upload: {photo_path}")
                except Exception as cleanup_error:
                    logger.error(f"Failed to cleanup file: {cleanup_error}")

            logger.exception("Database error creating user: %s", db_error)
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error creating user: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )


@router.get("/{user_id}", response_model=UserOut, summary="Get User by ID")
@owner_or_admin_endpoint("user_id")
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve a specific user by ID.

    - **user_id**: The ID of the user to retrieve

    Returns the user object with public information.
    Users can only access their own profile, admins can access any profile.
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        logger.info(f"User {current_user.email} accessed profile of user {user_id}")
        return user
    except HTTPException:
        raise
    except SQLAlchemyError:
        logger.exception("Error retrieving user")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user",
        )


@router.put("/{user_id}", response_model=UserOut, summary="Update User")
@owner_or_admin_endpoint("user_id")
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a user's information.

    - **user_id**: The ID of the user to update
    - **user_update**: Updated user information

    Returns the updated user object.
    Users can only update their own profile, admins can update any profile.
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        # Update only provided fields
        if user_update.name is not None:
            user.name = user_update.name
        if user_update.chanting_rounds is not None:
            user.chanting_rounds = user_update.chanting_rounds

        db.commit()
        db.refresh(user)

        logger.info(f"User {current_user.email} updated user {user.email}")
        return user

    except HTTPException:
        raise
    except SQLAlchemyError:
        logger.exception("Error updating user")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user",
        )


@router.get("/{user_id}/photo", summary="Get User Photo")
@owner_or_admin_endpoint("user_id")
async def get_user_photo(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve a user's profile photo.

    - **user_id**: The ID of the user whose photo to retrieve

    Returns the photo file or 404 if not found.
    Users can only access their own photos, admins can access any photo.
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user is None or not user.photo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found"
            )

        photo_path = Path(user.photo)
        if not photo_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Photo file not found",
            )

        logger.info(f"User {current_user.email} accessed photo of user {user_id}")
        return FileResponse(
            path=photo_path,
            media_type="image/jpeg",
            filename=f"user_{user_id}_photo.jpg",
        )

    except HTTPException:
        raise
    except SQLAlchemyError:
        logger.exception("Error retrieving user photo")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve photo",
        )
