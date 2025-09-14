"""
Authentication API endpoints.

This module contains all authentication-related routes including signup, login,
and JWT token management.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    get_password_hash,
    verify_password,
)
from app.db.models import User
from app.db.session import SessionLocal
from app.schemas.user import Token, UserLogin, UserSignup

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


@router.post("/signup", response_model=Token, summary="User Registration")
def signup(user_data: UserSignup, db: Session = Depends(get_db)):
    """
    Create a new user account and return JWT token.

    - **name**: User's full name (required)
    - **email**: Valid email address (required, must be unique)
    - **password**: Password with minimum 8 characters (required)
    - **chanting_rounds**: Daily chanting rounds 0-1000 (required)

    Returns a JWT access token for immediate authentication.
    """
    try:
        # Check if user already exists
        existing_user = (
            db.query(User).filter(User.email == user_data.email.lower()).first()
        )
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        # Hash the password
        hashed_pwd = get_password_hash(user_data.password)  # Not a hardcoded password

        # Create new user
        db_user = User(
            name=user_data.name,
            email=user_data.email.lower().strip(),
            password_hash=hashed_pwd,
            chanting_rounds=user_data.chanting_rounds,
        )

        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        # Create access token
        access_token = create_access_token(data={"sub": db_user.email})

        logger.info(f"New user registered: {db_user.email}")
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.jwt_access_token_expire_minutes * 60,
        }

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    except SQLAlchemyError:
        logger.exception("Error creating user")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user",
        )


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
