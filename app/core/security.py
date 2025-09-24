"""
Authentication utilities for JWT tokens and password hashing.

This module provides secure authentication functions using bcrypt for password
hashing and JWT for token-based authentication.
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt  # type: ignore
from passlib.context import CryptContext  # type: ignore
from sqlalchemy.orm import Session

from app.core.config import settings
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


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: The data to encode in the token (typically user info)
        expires_delta: Optional custom expiration time

    Returns:
        The encoded JWT token string
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """
    Verify and decode a JWT token.

    Args:
        token: The JWT token to verify

    Returns:
        The decoded token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError:
        return None


def get_user_from_token(token: str) -> Optional[str]:
    """
    Extract user email from a JWT token.

    Args:
        token: The JWT token

    Returns:
        User email if token is valid, None otherwise
    """
    payload = verify_token(token)
    if payload is None:
        return None

    email = payload.get("sub")
    return email if isinstance(email, str) else None


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
    from app.db.models import Devotee

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Extract and verify token
        token = credentials.credentials
        payload = verify_token(token)

        if payload is None:
            raise credentials_exception

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


def get_current_admin_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """
    Dependency to get current authenticated admin devotee.

    Args:
        credentials: HTTP Bearer authorization credentials
        db: Database session

    Returns:
        Current authenticated admin devotee

    Raises:
        HTTPException: If token is invalid, devotee not found, or not admin
    """
    from app.db.models import UserRole

    current_devotee = get_current_user(credentials, db)

    if current_devotee.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )

    return current_devotee


def create_devotee_token(devotee, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT token for a specific devotee.

    Args:
        devotee: Devotee object with email and id attributes
        expires_delta: Optional custom expiration time

    Returns:
        JWT token string
    """
    data = {
        "sub": str(devotee.id),  # Use devotee ID as subject for new tokens
        "email": devotee.email,
        "role": "devotee",  # All devotees have devotee role for API access
        "devotee_role": devotee.role.value,  # Actual admin/user role
    }
    return create_access_token(data, expires_delta)


# Backward compatibility alias
def create_user_token(user, expires_delta: Optional[timedelta] = None) -> str:
    """
    Legacy function for backward compatibility.
    Use create_devotee_token for new code.
    """
    return create_devotee_token(user, expires_delta)


def verify_user_token(token: str):
    """
    Verify token and return user information.

    Args:
        token: JWT token string

    Returns:
        Dictionary with user info if valid, None otherwise
    """
    payload = verify_token(token)
    if payload is None:
        return None

    return {
        "email": payload.get("sub"),
        "user_id": payload.get("user_id"),
        "role": payload.get("role"),
    }


def check_devotee_access(current_devotee, target_devotee_id: int) -> bool:
    """
    Check if current devotee can access another devotee's data.

    Args:
        current_devotee: Current authenticated devotee
        target_devotee_id: ID of devotee being accessed

    Returns:
        True if access allowed, False otherwise
    """
    from app.db.models import UserRole

    # Admin can access anyone
    if current_devotee.role == UserRole.ADMIN:
        return True

    # Devotees can only access their own data
    return current_devotee.id == target_devotee_id


# Backward compatibility alias
def check_user_access(current_user, target_user_id: int) -> bool:
    """
    Legacy function for backward compatibility.
    Use check_devotee_access for new code.
    """
    return check_devotee_access(current_user, target_user_id)


def generate_password_reset_token(email: str) -> str:
    """
    Generate a secure password reset token.

    Args:
        email: User's email address

    Returns:
        Password reset token
    """
    import secrets
    from datetime import datetime, timezone

    # Create token data
    token_data = {
        "sub": email,
        "type": "password_reset",
        "iat": datetime.now(timezone.utc).timestamp(),
        "nonce": secrets.token_hex(8),  # Add randomness
    }

    # Create token with custom expiration
    expires_delta = timedelta(hours=settings.password_reset_token_expire_hours)
    return create_access_token(token_data, expires_delta)


def verify_password_reset_token(token: str) -> Optional[str]:
    """
    Verify password reset token and return user email.

    Args:
        token: Password reset token

    Returns:
        User email if token is valid, None otherwise
    """
    payload = verify_token(token)
    if payload is None:
        return None

    # Check if it's a password reset token
    if payload.get("type") != "password_reset":
        return None

    # Extract email
    email = payload.get("sub")
    return email if isinstance(email, str) else None


def is_token_expired(user) -> bool:
    """
    Check if user's password reset token has expired.

    Args:
        user: User object with password_reset_expires field

    Returns:
        True if token expired or doesn't exist, False otherwise
    """
    if not user.password_reset_expires:
        return True

    from datetime import datetime, timezone

    return user.password_reset_expires <= datetime.now(timezone.utc)


def clear_reset_token(user, db_session) -> None:
    """
    Clear user's password reset token and expiration.

    Args:
        user: User object
        db_session: Database session
    """
    user.password_reset_token = None
    user.password_reset_expires = None
    db_session.commit()
