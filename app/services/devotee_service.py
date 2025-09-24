"""
Enhanced devotee business logic service.

This service encapsulates devotee-related business logic with optimized
query methods, search functionality, and comprehensive business rules.
Designed for high performance with 100K users.
"""

import logging
import secrets
from datetime import date, datetime, timedelta, timezone
from math import ceil
from pathlib import Path
from typing import List, Optional

from fastapi import HTTPException, UploadFile, status
from pydantic import EmailStr
from sqlalchemy import desc, func, or_, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_password_hash, verify_password
from app.db.models import (
    Devotee,
    InitiationStatus,
    MaritalStatus,
)
from app.schemas.devotee import (
    DevoteeCreate,
    DevoteeListResponse,
    DevoteeSearchFilters,
    DevoteeStatsResponse,
    DevoteeUpdate,
)
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)


class DevoteeService:
    """
    Enhanced service class for devotee business logic with performance optimizations.

    Features:
    - Efficient search with proper indexing
    - Optimized pagination
    - Comprehensive filtering
    - Statistics and analytics
    - Business rule validation
    """

    def __init__(self, db: Session):
        self.db = db
        self.upload_dir = Path(settings.upload_directory)
        self.upload_dir.mkdir(exist_ok=True)

    def create_devotee(
        self,
        db: Session,
        devotee_data: DevoteeCreate,
        photo: Optional[UploadFile] = None,
    ) -> Devotee:
        """
        Create a new devotee with comprehensive validation and optimization.

        Args:
            db: Database session
            devotee_data: Devotee creation data
            photo: Optional photo file

        Returns:
            Created Devotee instance

        Raises:
            HTTPException: If devotee already exists or validation fails
        """
        # Check if devotee exists
        existing_devotee = self.get_devotee_by_email(db, devotee_data.email)
        if existing_devotee:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Devotee with this email already exists",
            )

        # Validate business rules
        self._validate_devotee_data(devotee_data)

        # Handle photo upload
        photo_path = None
        if photo:
            photo_path = self._save_photo(photo, devotee_data.email)

        # Prepare children data
        children_json = None
        if devotee_data.children:
            children_json = {
                "count": len(devotee_data.children),
                "children": [child.model_dump() for child in devotee_data.children],
                "updated_at": datetime.utcnow().isoformat(),
            }

        # Create devotee
        db_devotee = Devotee(
            # Authentication
            email=devotee_data.email.lower(),
            password_hash=get_password_hash(devotee_data.password),
            # Personal Information
            legal_name=devotee_data.legal_name.strip(),
            date_of_birth=devotee_data.date_of_birth,
            gender=devotee_data.gender,
            marital_status=devotee_data.marital_status,
            # Contact Information
            country_code=devotee_data.country_code,
            mobile_number=devotee_data.mobile_number,
            national_id=devotee_data.national_id,
            # Family Information
            father_name=devotee_data.father_name.strip(),
            mother_name=devotee_data.mother_name.strip(),
            spouse_name=(
                devotee_data.spouse_name.strip() if devotee_data.spouse_name else None
            ),
            date_of_marriage=devotee_data.date_of_marriage,
            children=children_json,
            # Location Information
            address=devotee_data.address.strip() if devotee_data.address else None,
            city=devotee_data.city.strip() if devotee_data.city else None,
            state_province=(
                devotee_data.state_province.strip()
                if devotee_data.state_province
                else None
            ),
            country=devotee_data.country.strip() if devotee_data.country else None,
            postal_code=(
                devotee_data.postal_code.strip() if devotee_data.postal_code else None
            ),
            # ISKCON Spiritual Information
            initiation_status=devotee_data.initiation_status,
            spiritual_master=(
                devotee_data.spiritual_master.strip()
                if devotee_data.spiritual_master
                else None
            ),
            initiation_date=devotee_data.initiation_date,
            initiation_place=(
                devotee_data.initiation_place.strip()
                if devotee_data.initiation_place
                else None
            ),
            spiritual_guide=(
                devotee_data.spiritual_guide.strip()
                if devotee_data.spiritual_guide
                else None
            ),
            # ISKCON Journey
            when_were_you_introduced_to_iskcon=devotee_data.when_were_you_introduced_to_iskcon,
            who_introduced_you_to_iskcon=(
                devotee_data.who_introduced_you_to_iskcon.strip()
                if devotee_data.who_introduced_you_to_iskcon
                else None
            ),
            which_iskcon_center_you_first_connected_to=(
                devotee_data.which_iskcon_center_you_first_connected_to.strip()
                if devotee_data.which_iskcon_center_you_first_connected_to
                else None
            ),
            # Chanting Practice
            chanting_number_of_rounds=devotee_data.chanting_number_of_rounds,
            chanting_16_rounds_since=devotee_data.chanting_16_rounds_since,
            # Devotional Education
            devotional_courses=(
                devotee_data.devotional_courses.strip()
                if devotee_data.devotional_courses
                else None
            ),
            # Photo
            photo=photo_path,
        )

        db.add(db_devotee)
        db.commit()
        db.refresh(db_devotee)

        logger.info(f"Created devotee: {db_devotee.email}")
        return db_devotee

    def get_devotees_with_filters(
        self, db: Session, filters: DevoteeSearchFilters
    ) -> DevoteeListResponse:
        """
        Get paginated list of devotees with comprehensive filtering and search.
        Optimized for performance with proper indexing.

        Args:
            db: Database session
            filters: Search and filter criteria

        Returns:
            Paginated devotee list response
        """
        query = db.query(Devotee)

        # Apply filters
        query = self._apply_search_filters(query, filters)

        # Get total count for pagination
        total = query.count()

        # Apply sorting
        query = self._apply_sorting(query, filters.sort_by, filters.sort_order)

        # Apply pagination
        offset = (filters.page - 1) * filters.limit
        devotees = query.offset(offset).limit(filters.limit).all()

        # Calculate pagination metadata
        total_pages = ceil(total / filters.limit)
        has_next = filters.page < total_pages
        has_prev = filters.page > 1

        return DevoteeListResponse(
            devotees=devotees,
            total=total,
            page=filters.page,
            limit=filters.limit,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev,
        )

    def get_devotee_by_id(self, db: Session, devotee_id: int) -> Optional[Devotee]:
        """Get devotee by ID with optimized query."""
        return db.query(Devotee).filter(Devotee.id == devotee_id).first()

    def get_devotee_by_email(self, db: Session, email: EmailStr) -> Optional[Devotee]:
        """Get devotee by email with optimized query."""
        return db.query(Devotee).filter(Devotee.email == email.lower()).first()

    def update_devotee(
        self,
        db: Session,
        devotee_id: int,
        devotee_update: DevoteeUpdate,
        photo: Optional[UploadFile] = None,
    ) -> Optional[Devotee]:
        """
        Update devotee information with validation and business rules.

        Args:
            db: Database session
            devotee_id: Devotee ID to update
            devotee_update: Update data
            photo: Optional new photo

        Returns:
            Updated Devotee or None if not found
        """
        devotee = self.get_devotee_by_id(db, devotee_id)
        if not devotee:
            return None

        # Validate business rules for update
        self._validate_devotee_update(devotee_update, devotee)

        # Update only provided fields
        update_data = devotee_update.model_dump(exclude_unset=True)

        # Handle children data
        if "children" in update_data and update_data["children"] is not None:
            children_json = {
                "count": len(update_data["children"]),
                "children": [
                    child.model_dump() if hasattr(child, "model_dump") else child
                    for child in update_data["children"]
                ],
                "updated_at": datetime.utcnow().isoformat(),
            }
            update_data["children"] = children_json

        # Handle photo upload
        if photo:
            # Remove old photo if exists (placeholder for now)
            # TODO: Implement cloud storage integration
            update_data["photo_path"] = self._save_photo(photo, devotee.email)

        # Apply updates with string trimming
        for field, value in update_data.items():
            if isinstance(value, str):
                value = value.strip() if value else None
            setattr(devotee, field, value)

        db.commit()
        db.refresh(devotee)

        logger.info(f"Updated devotee: {devotee.email}")
        return devotee

    def get_devotee_statistics(self, db: Session) -> DevoteeStatsResponse:
        """
        Get comprehensive devotee statistics for dashboard and analytics.
        Uses optimized queries with proper aggregation.

        Returns:
            Comprehensive statistics response
        """
        # Total devotees
        total_devotees = db.query(func.count(Devotee.id)).scalar()

        # Recently joined (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recently_joined = (
            db.query(func.count(Devotee.id))
            .filter(Devotee.created_at >= thirty_days_ago)
            .scalar()
        )

        # Statistics by country (top 10)
        by_country = dict(
            db.query(Devotee.country, func.count(Devotee.id))
            .filter(Devotee.country.isnot(None))
            .group_by(Devotee.country)
            .order_by(desc(func.count(Devotee.id)))
            .limit(10)
            .all()
        )

        # Statistics by initiation status
        by_initiation_status = dict(
            db.query(Devotee.initiation_status, func.count(Devotee.id))
            .filter(Devotee.initiation_status.isnot(None))
            .group_by(Devotee.initiation_status)
            .all()
        )

        # Statistics by gender
        by_gender = dict(
            db.query(Devotee.gender, func.count(Devotee.id))
            .group_by(Devotee.gender)
            .all()
        )

        # Statistics by marital status
        by_marital_status = dict(
            db.query(Devotee.marital_status, func.count(Devotee.id))
            .group_by(Devotee.marital_status)
            .all()
        )

        # Average age calculation
        avg_age_query = db.query(
            func.avg(
                func.timestampdiff(text("YEAR"), Devotee.date_of_birth, func.curdate())
            ).label("avg_age")
        ).first()
        average_age = float(avg_age_query.avg_age) if avg_age_query.avg_age else None

        # Average chanting rounds
        avg_rounds_query = (
            db.query(func.avg(Devotee.chanting_number_of_rounds).label("avg_rounds"))
            .filter(Devotee.chanting_number_of_rounds.isnot(None))
            .first()
        )
        average_chanting_rounds = (
            float(avg_rounds_query.avg_rounds) if avg_rounds_query.avg_rounds else None
        )

        return DevoteeStatsResponse(
            total_devotees=total_devotees,
            by_country=by_country,
            by_initiation_status=by_initiation_status,
            by_gender=by_gender,
            by_marital_status=by_marital_status,
            average_age=average_age,
            average_chanting_rounds=average_chanting_rounds,
            recently_joined=recently_joined,
        )

    def search_devotees_by_text(
        self, db: Session, search_text: str, limit: int = 20
    ) -> List[Devotee]:
        """
        Perform fast text search across multiple fields.
        Uses optimized LIKE queries with proper indexing.

        Args:
            db: Database session
            search_text: Text to search for
            limit: Maximum results to return

        Returns:
            List of matching devotees
        """
        search_pattern = f"%{search_text.lower()}%"

        return (
            db.query(Devotee)
            .filter(
                or_(
                    func.lower(Devotee.legal_name).like(search_pattern),
                    func.lower(Devotee.email).like(search_pattern),
                    func.lower(Devotee.city).like(search_pattern),
                    func.lower(Devotee.country).like(search_pattern),
                    func.lower(Devotee.spiritual_master).like(search_pattern),
                )
            )
            .order_by(Devotee.legal_name)
            .limit(limit)
            .all()
        )

    def get_devotees_by_location(
        self,
        db: Session,
        country: Optional[str] = None,
        state: Optional[str] = None,
        city: Optional[str] = None,
    ) -> List[Devotee]:
        """
        Get devotees by location using optimized queries with proper indexes.

        Args:
            db: Database session
            country: Country filter
            state: State/Province filter
            city: City filter

        Returns:
            List of devotees matching location criteria
        """
        query = db.query(Devotee)

        if country:
            query = query.filter(func.lower(Devotee.country) == country.lower())
        if state:
            query = query.filter(func.lower(Devotee.state_province) == state.lower())
        if city:
            query = query.filter(func.lower(Devotee.city) == city.lower())

        return query.order_by(Devotee.legal_name).all()

    def get_devotees_by_spiritual_master(
        self, db: Session, spiritual_master: str
    ) -> List[Devotee]:
        """Get devotees by spiritual master with optimized query."""
        return (
            db.query(Devotee)
            .filter(func.lower(Devotee.spiritual_master) == spiritual_master.lower())
            .order_by(Devotee.legal_name)
            .all()
        )

    # Authentication methods
    async def create_simple_unverified_devotee(self, devotee_data) -> Devotee:
        """Create an unverified devotee with minimal information and send verification email."""
        # Check if devotee already exists
        existing_devotee = (
            self.db.query(Devotee)
            .filter(Devotee.email == devotee_data.email.lower())
            .first()
        )

        if existing_devotee:
            if existing_devotee.email_verified is True:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A verified devotee with this email already exists",
                )
            # Resend verification email for unverified devotee
            await self._send_verification_email(existing_devotee)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Devotee exists but is not verified. Verification email sent again.",
            )

        # Generate secure verification token
        verification_token = secrets.token_urlsafe(32)
        verification_expires = datetime.now(timezone.utc) + timedelta(hours=24)

        # Create new devotee with minimal information (unverified)
        new_devotee = Devotee(
            # Basic authentication fields
            email=devotee_data.email.lower(),
            password_hash=get_password_hash(devotee_data.password),
            # Minimal profile information
            legal_name=devotee_data.name.strip(),
            # Verification fields
            email_verified=False,
            verification_token=verification_token,
            verification_expires=verification_expires,
            # Set default spiritual information
            initiation_status=InitiationStatus.ASPIRING,
            chanting_number_of_rounds=16,
        )

        try:
            self.db.add(new_devotee)
            self.db.flush()  # Get the ID without committing

            # Send verification email
            await self._send_verification_email(new_devotee)

            self.db.commit()
            self.db.refresh(new_devotee)

            logger.info(
                f"Created simple unverified devotee with email: {devotee_data.email}"
            )
            return new_devotee

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create simple unverified devotee: {e!s}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create devotee account",
            ) from None

    async def create_unverified_devotee(
        self, devotee_data: DevoteeCreate, photo: Optional[UploadFile] = None
    ) -> Devotee:
        """Create an unverified devotee and send verification email."""
        # Check if devotee already exists
        existing_devotee = self.get_devotee_by_email(self.db, devotee_data.email)
        if existing_devotee:
            if getattr(existing_devotee, "email_verified", False) is True:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A verified devotee with this email already exists",
                )
            # Resend verification email for unverified devotee
            await self._send_verification_email(existing_devotee)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Devotee exists but is not verified. Verification email sent again.",
            )

        # Generate secure verification token
        from app.core.auth_security import token_manager

        verification_token = token_manager.generate_verification_token(
            devotee_data.email
        )
        verification_expires = datetime.now(timezone.utc) + timedelta(hours=24)

        # Create new devotee (unverified)
        devotee_dict = devotee_data.model_dump()
        devotee_dict.update(
            {
                "email_verified": False,
                "verification_token": verification_token,
                "verification_expires": verification_expires,
            }
        )

        new_devotee = Devotee(**devotee_dict)

        try:
            self.db.add(new_devotee)
            self.db.flush()  # Get the ID without committing

            # Save photo if provided
            if photo:
                self._save_photo(photo, devotee_data.email)

            # Send verification email
            await self._send_verification_email(new_devotee)

            self.db.commit()
            self.db.refresh(new_devotee)

            logger.info(f"Created unverified devotee with email: {devotee_data.email}")
            return new_devotee

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create unverified devotee: {e!s}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create devotee account",
            )

    async def verify_devotee_email(self, token: str) -> str:
        """Verify devotee's email using verification token.

        Returns:
            str: The verified email address
        """
        devotee = (
            self.db.query(Devotee).filter(Devotee.verification_token == token).first()
        )

        if not devotee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid or expired verification token",
            )

        # Check if already verified
        if getattr(devotee, "email_verified", False) is True:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already verified",
            )

        # Check if token is expired with proper timezone handling
        if devotee.verification_expires is not None:
            current_time = datetime.now(timezone.utc)
            expires_at = devotee.verification_expires

            # Handle timezone awareness - if tzinfo is None, assume UTC
            if hasattr(expires_at, "tzinfo") and expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)

            if expires_at < current_time:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Verification token has expired",
                )

        try:
            # Store email before marking as verified
            verified_email = devotee.email

            # Mark devotee as verified
            devotee.email_verified = True
            devotee.verification_token = None
            devotee.verification_expires = None

            self.db.commit()

            # Send success email
            try:
                email_service = EmailService()
                await email_service.send_email_verification_success(
                    verified_email, devotee.legal_name
                )
            except Exception as email_error:
                logger.warning(
                    f"Failed to send verification success email: {email_error}"
                )
                # Continue with verification even if email fails

            logger.info(f"Verified devotee email: {verified_email}")
            return verified_email

        except Exception as e:
            logger.error(f"Failed to verify devotee email: {e!s}")
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to verify email",
            ) from None

    async def resend_verification_email(self, email: str) -> bool:
        """Resend verification email to devotee."""
        devotee = self.get_devotee_by_email(self.db, email)
        if not devotee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Devotee not found",
            )

        # Check if already verified - ensure we get the actual boolean value
        already_verified = getattr(devotee, "email_verified", False)
        if already_verified is True:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already verified",
            )

        try:
            # Generate new verification token
            devotee.verification_token = secrets.token_urlsafe(32)
            devotee.verification_expires = datetime.now(timezone.utc) + timedelta(
                hours=24
            )

            await self._send_verification_email(devotee)

            self.db.commit()
            logger.info(f"Resent verification email to: {email}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to resend verification email: {e!s}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to resend verification email",
            )

    async def _send_verification_email(self, devotee: Devotee):
        """Send verification email to devotee."""
        email_service = EmailService()
        await email_service.send_email_verification(
            email=devotee.email,
            user_name=devotee.legal_name,
            verification_token=devotee.verification_token,
        )

    async def send_password_reset_email(self, email: str) -> bool:
        """Send password reset email to devotee."""
        devotee = self.get_devotee_by_email(self.db, email)
        if not devotee:
            # Don't reveal if email exists for security
            return True

        if getattr(devotee, "email_verified", False) is not True:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email must be verified before password reset",
            )

        try:
            # Generate reset token
            devotee.reset_token = secrets.token_urlsafe(32)
            devotee.reset_expires = datetime.now(timezone.utc) + timedelta(hours=1)

            # Send reset email
            email_service = EmailService()
            await email_service.send_password_reset_email(
                email=devotee.email,
                name=devotee.legal_name,
                reset_token=devotee.reset_token,
            )

            self.db.commit()
            logger.info(f"Sent password reset email to: {email}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to send password reset email: {e!s}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send password reset email",
            ) from None

    def reset_password_with_token(self, token: str, new_password: str) -> bool:
        """Reset devotee's password using reset token."""
        devotee = self.db.query(Devotee).filter(Devotee.reset_token == token).first()

        if not devotee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid reset token",
            )

        # Check if token is expired
        if devotee.reset_expires < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token has expired",
            )

        try:
            # Update password and clear reset token
            devotee.password_hash = get_password_hash(new_password)
            devotee.reset_token = None
            devotee.reset_expires = None

            self.db.commit()
            logger.info(f"Password reset successful for devotee: {devotee.email}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to reset password: {e!s}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to reset password",
            ) from None

    def admin_reset_password(
        self, devotee_id: int, new_password: str, admin_id: int
    ) -> bool:
        """Admin function to reset any devotee's password."""
        devotee = self.get_devotee_by_id(self.db, devotee_id)
        if not devotee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Devotee not found",
            )

        try:
            devotee.password_hash = get_password_hash(new_password)

            self.db.commit()
            logger.info(f"Admin {admin_id} reset password for devotee {devotee_id}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to admin reset password: {e!s}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to reset password",
            ) from None

    def authenticate_devotee(self, email: str, password: str) -> Optional[Devotee]:
        """Authenticate devotee with email and password."""
        devotee = self.get_devotee_by_email(self.db, email)
        if not devotee:
            return None

        if getattr(devotee, "email_verified", False) is not True:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email must be verified before login",
            )

        if not verify_password(password, devotee.password_hash):
            return None

        return devotee

    def _apply_search_filters(self, query, filters: DevoteeSearchFilters):
        """Apply search filters to query with optimal performance."""

        # Text search across multiple fields
        if filters.search:
            search_pattern = f"%{filters.search.lower()}%"
            query = query.filter(
                or_(
                    func.lower(Devotee.legal_name).like(search_pattern),
                    func.lower(Devotee.email).like(search_pattern),
                    func.lower(Devotee.city).like(search_pattern),
                    func.lower(Devotee.country).like(search_pattern),
                    func.lower(Devotee.spiritual_master).like(search_pattern),
                )
            )

        # Location filters (use indexes)
        if filters.country:
            query = query.filter(func.lower(Devotee.country) == filters.country.lower())
        if filters.state_province:
            query = query.filter(
                func.lower(Devotee.state_province) == filters.state_province.lower()
            )
        if filters.city:
            query = query.filter(func.lower(Devotee.city) == filters.city.lower())

        # Spiritual filters (use indexes)
        if filters.initiation_status:
            query = query.filter(Devotee.initiation_status == filters.initiation_status)
        if filters.spiritual_master:
            query = query.filter(
                func.lower(Devotee.spiritual_master) == filters.spiritual_master.lower()
            )

        # Demographic filters
        if filters.gender:
            query = query.filter(Devotee.gender == filters.gender)
        if filters.marital_status:
            query = query.filter(Devotee.marital_status == filters.marital_status)

        # Age range filters
        if filters.min_age or filters.max_age:
            today = date.today()

            if filters.min_age:
                max_birth_date = date(
                    today.year - filters.min_age, today.month, today.day
                )
                query = query.filter(Devotee.date_of_birth <= max_birth_date)

            if filters.max_age:
                min_birth_date = date(
                    today.year - filters.max_age, today.month, today.day
                )
                query = query.filter(Devotee.date_of_birth >= min_birth_date)

        # Chanting rounds filters
        if filters.min_rounds:
            query = query.filter(
                Devotee.chanting_number_of_rounds >= filters.min_rounds
            )
        if filters.max_rounds:
            query = query.filter(
                Devotee.chanting_number_of_rounds <= filters.max_rounds
            )

        return query

    def _apply_sorting(self, query, sort_by: str, sort_order: str):
        """Apply sorting to query with proper field mapping."""
        sort_fields = {
            "legal_name": Devotee.legal_name,
            "created_at": Devotee.created_at,
            "city": Devotee.city,
            "country": Devotee.country,
            "initiation_status": Devotee.initiation_status,
            "chanting_rounds": Devotee.chanting_number_of_rounds,
            "date_of_birth": Devotee.date_of_birth,
        }

        sort_field = sort_fields.get(sort_by, Devotee.created_at)

        if sort_order == "desc":
            query = query.order_by(desc(sort_field))
        else:
            query = query.order_by(sort_field)

        return query

    def _validate_devotee_data(self, devotee_data: DevoteeCreate) -> None:
        """Validate devotee data according to business rules."""

        # Marriage validation
        if devotee_data.marital_status == MaritalStatus.MARRIED:
            if not devotee_data.spouse_name:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Spouse name is required for married devotees",
                )

        # Initiation validation
        if devotee_data.initiation_status in [
            InitiationStatus.HARINAM,
            InitiationStatus.BRAHMIN,
        ]:
            if not devotee_data.spiritual_master:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Spiritual master is required for initiated devotees",
                )
            if not devotee_data.initiation_date:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Initiation date is required for initiated devotees",
                )

    def _validate_devotee_update(
        self, devotee_update: DevoteeUpdate, existing_devotee: Devotee
    ) -> None:
        """Validate devotee update data according to business rules."""

        # Marriage validation for updates
        # Only validate if explicitly setting marital status to married
        if devotee_update.marital_status == MaritalStatus.MARRIED:
            # Get the spouse name from update or existing record
            spouse_name = devotee_update.spouse_name
            if not spouse_name:
                # Try to get from existing devotee (avoid SQLAlchemy column issues)
                try:
                    existing_spouse = getattr(existing_devotee, "spouse_name", None)
                    spouse_name = existing_spouse
                except Exception:
                    spouse_name = None

            # Check if spouse name is missing or empty
            if not spouse_name or (
                isinstance(spouse_name, str) and spouse_name.strip() == ""
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Spouse name is required for married devotees",
                )

    def _save_photo(self, photo: UploadFile, devotee_email: str) -> str:
        """Save uploaded photo and return relative path."""
        # Validate file
        if not photo.content_type or not photo.content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only image files are allowed",
            )

        # Generate filename
        file_extension = (
            photo.filename.split(".")[-1].lower() if photo.filename else "jpg"
        )
        safe_email = devotee_email.replace("@", "_at_").replace(".", "_")
        timestamp = int(datetime.utcnow().timestamp())
        filename = f"devotee_{safe_email}_{timestamp}.{file_extension}"
        file_path = self.upload_dir / filename

        # Save file
        try:
            with open(file_path, "wb") as buffer:
                content = photo.file.read()
                buffer.write(content)

            logger.info(f"Saved photo: {filename}")
            return str(file_path)

        except Exception as e:
            logger.error(f"Failed to save photo: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save photo",
            )

    async def complete_devotee_profile(
        self,
        user_id: int,
        profile_data: dict,
        photo: Optional[UploadFile] = None,
    ) -> bool:
        """Complete devotee profile after email verification."""
        devotee = self.get_devotee_by_id(self.db, user_id)
        if not devotee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Devotee not found",
            )

        # Check if email is verified
        if getattr(devotee, "email_verified", False) is not True:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email must be verified before completing profile",
            )

        try:
            # Update devotee with profile data
            for field, value in profile_data.items():
                if hasattr(devotee, field):
                    setattr(devotee, field, value)

            # Handle photo upload
            if photo:
                photo_path = self._save_photo(photo, devotee.email)
                devotee.photo = photo_path

            self.db.commit()
            logger.info(f"Completed profile for devotee: {devotee.email}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to complete devotee profile: {e!s}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to complete profile",
            ) from None


# Note: Global service instance removed due to db session requirement
# Use DevoteeService(db) in each endpoint instead
