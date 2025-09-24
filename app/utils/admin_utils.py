"""
Admin user seeding and management utilities.

This module provides utilities for creating initial admin users
and managing user roles in the system.
"""

import logging
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Devotee, UserRole
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


def create_admin_user(
    name: str,
    email: str,
    secret: str,
    chanting_rounds: int = 16,
    db: Optional[Session] = None,
) -> Devotee:
    """
    Create an admin user in the system.

    Args:
        name: Admin user's full name
        email: Admin user's email (must be unique)
        secret: Admin user's password (will be hashed)
        chanting_rounds: Daily chanting rounds (default: 16)
        db: Optional database session (creates new if not provided)

    Returns:
        Created admin user object

    Raises:
        IntegrityError: If email already exists
        Exception: For other database errors
    """
    db_session = db or SessionLocal()

    try:
        # Check if user already exists
        existing_user = (
            db_session.query(Devotee).filter(Devotee.email == email.lower()).first()
        )
        if existing_user:
            logger.warning(f"Devotee with email {email} already exists")
            if existing_user.role != UserRole.ADMIN:
                # Promote existing user to admin
                existing_user.role = UserRole.ADMIN
                db_session.commit()
                db_session.refresh(existing_user)
                logger.info(f"Promoted existing user {email} to admin")
            return existing_user

        # Create new admin user
        from app.core.security import get_password_hash as hash_func

        hashed_value = hash_func(secret)
        admin_user = Devotee(
            legal_name=name.strip(),
            email=email.lower().strip(),
            password_hash=hashed_value,
            role=UserRole.ADMIN,
            chanting_number_of_rounds=chanting_rounds,
        )

        db_session.add(admin_user)
        db_session.commit()
        db_session.refresh(admin_user)

        logger.info(f"Created admin user: {email}")
        return admin_user

    except IntegrityError as e:
        db_session.rollback()
        logger.error(f"Failed to create admin user - email conflict: {e}")
        raise
    except Exception as e:
        db_session.rollback()
        logger.error(f"Failed to create admin user: {e}")
        raise
    finally:
        if not db:  # Only close if we created the session
            db_session.close()


def ensure_admin_exists() -> bool:
    """
    Check if at least one admin user exists in the system.

    Returns:
        True if admin exists, False if no admin found or error
    """
    db = SessionLocal()

    try:
        # Check if any admin exists
        admin_count = db.query(Devotee).filter(Devotee.role == UserRole.ADMIN).count()

        if admin_count > 0:
            logger.info(f"Found {admin_count} admin user(s) in system")
            return True
        logger.warning(
            "No admin users found in system. "
            "Use promote_user_to_admin() or create_admin_user() to create one."
        )
        return False

    except Exception as e:
        logger.error(f"Failed to check admin existence: {e}")
        return False
    finally:
        db.close()


def promote_user_to_admin(email: str, db: Optional[Session] = None) -> bool:
    """
    Promote an existing user to admin role.

    Args:
        email: Email of user to promote
        db: Optional database session

    Returns:
        True if user was promoted, False if user not found or error
    """
    db_session = db or SessionLocal()

    try:
        user = db_session.query(Devotee).filter(Devotee.email == email.lower()).first()
        if not user:
            logger.error(f"Devotee not found: {email}")
            return False

        if user.role == UserRole.ADMIN:
            logger.info(f"Devotee {email} is already an admin")
            return True

        user.role = UserRole.ADMIN
        db_session.commit()
        db_session.refresh(user)

        logger.info(f"Promoted user {email} to admin")
        return True

    except Exception as e:
        db_session.rollback()
        logger.error(f"Failed to promote user {email} to admin: {e}")
        return False
    finally:
        if not db:
            db_session.close()


def demote_admin_to_user(email: str, db: Optional[Session] = None) -> bool:
    """
    Demote an admin user to regular user role.

    Args:
        email: Email of admin to demote
        db: Optional database session

    Returns:
        True if admin was demoted, False if user not found or error
    """
    db_session = db or SessionLocal()

    try:
        user = db_session.query(Devotee).filter(Devotee.email == email.lower()).first()
        if not user:
            logger.error(f"Devotee not found: {email}")
            return False

        if user.role != UserRole.ADMIN:
            logger.info(f"Devotee {email} is not an admin")
            return True

        # Check if this is the last admin
        admin_count = (
            db_session.query(Devotee).filter(Devotee.role == UserRole.ADMIN).count()
        )
        if admin_count <= 1:
            logger.error("Cannot demote last admin user")
            return False

        user.role = UserRole.USER
        db_session.commit()
        db_session.refresh(user)

        logger.info(f"Demoted admin {email} to regular user")
        return True

    except Exception as e:
        db_session.rollback()
        logger.error(f"Failed to demote admin {email}: {e}")
        return False
    finally:
        if not db:
            db_session.close()


def list_admin_users(db: Optional[Session] = None) -> list[Devotee]:
    """
    Get list of all admin users.

    Args:
        db: Optional database session

    Returns:
        List of admin user objects
    """
    db_session = db or SessionLocal()

    try:
        admins = db_session.query(Devotee).filter(Devotee.role == UserRole.ADMIN).all()
        logger.info(f"Found {len(admins)} admin users")
        return admins
    except Exception as e:
        logger.error(f"Failed to list admin users: {e}")
        return []
    finally:
        if not db:
            db_session.close()
