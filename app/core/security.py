"""
Authentication utilities for JWT tokens and password hashing.

This module provides secure authentication functions using bcrypt for password
hashing and JWT for token-based authentication.
"""

from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt  # type: ignore
from passlib.context import CryptContext  # type: ignore
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Devotee
from app.db.session import get_db

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against its hash.

    Args:
        plain_password: The plaintext password to verify
        hashed_password: The hashed password from database

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a plaintext password.

    Args:
        password: The plaintext password to hash

    Returns:
        The hashed password string
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: The data to encode in the token (typically user info)
        expires_delta: Optional custom expiration time

    Returns:
        JWT access token string
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_expiration_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt


# Security scheme for JWT Bearer tokens
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
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

        # Handle both old user tokens (email in 'sub') and new devotee tokens (devotee_id in 'sub')
        user_identifier = payload.get("sub")
        if user_identifier is None:
            raise credentials_exception

        # Try to get devotee by ID first (new format), then by email (legacy format)
        devotee = None
        try:
            devotee_id = int(user_identifier)
            devotee = db.query(Devotee).filter(Devotee.id == devotee_id).first()
        except (ValueError, TypeError):
            # If not a valid integer, treat as email (legacy token format)
            devotee = db.query(Devotee).filter(Devotee.email == user_identifier).first()

        if devotee is None:
            raise credentials_exception

        return devotee

    except JWTError:
        raise credentials_exception
