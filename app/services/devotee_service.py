"""
Enhanced devotee business logic service.

This service encapsulates devotee-related business logic with optimized
query methods, search functionality, and comprehensive business rules.
Designed for high performance with 100K users.
"""

import logging
import secrets
from datetime import UTC, datetime, timedelta
from math import ceil
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from pydantic import EmailStr
from sqlalchemy import desc, func, or_, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.responses import StandardHTTPException
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
from app.services.gmail_service import GmailService
from app.services.storage_service import StorageService

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

    def create_devotee(
        self,
        db: Session,
        devotee_data: DevoteeCreate,
        photo: UploadFile | None = None,
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
            raise StandardHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Devotee with this email already exists",
                success=False,
                data=None,
            )

        # Validate business rules
        self._validate_devotee_data(devotee_data)

        # Handle photo upload
        # For new devotees, we don't have user_id yet, so we'll skip photo upload during creation
        # Photo can be uploaded later during profile completion
        photo_path = None
        if photo:
            logger.info(
                "Photo upload during signup is deprecated. Use complete-profile endpoint instead."
            )

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
            spouse_name=(devotee_data.spouse_name.strip() if devotee_data.spouse_name else None),
            date_of_marriage=devotee_data.date_of_marriage,
            children=children_json,
            # Location Information
            address=devotee_data.address.strip() if devotee_data.address else None,
            city=devotee_data.city.strip() if devotee_data.city else None,
            state_province=(
                devotee_data.state_province.strip() if devotee_data.state_province else None
            ),
            country=devotee_data.country.strip() if devotee_data.country else None,
            postal_code=(devotee_data.postal_code.strip() if devotee_data.postal_code else None),
            # ISKCON Spiritual Information
            initiation_status=devotee_data.initiation_status,
            spiritual_master=(
                devotee_data.spiritual_master.strip() if devotee_data.spiritual_master else None
            ),
            initiation_date=devotee_data.initiation_date,
            initiation_place=(
                devotee_data.initiation_place.strip() if devotee_data.initiation_place else None
            ),
            spiritual_guide=(
                devotee_data.spiritual_guide.strip() if devotee_data.spiritual_guide else None
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
                devotee_data.devotional_courses.strip() if devotee_data.devotional_courses else None
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

    def get_devotee_by_id(self, db: Session, devotee_id: int) -> Devotee | None:
        """Get devotee by ID with optimized query."""
        return db.query(Devotee).filter(Devotee.id == devotee_id).first()

    def get_devotee_by_email(self, db: Session, email: EmailStr) -> Devotee | None:
        """Get devotee by email with optimized query."""
        return db.query(Devotee).filter(Devotee.email == email.lower()).first()

    def _validate_devotee_update(
        self, devotee_update: DevoteeUpdate, existing_devotee: Devotee
    ) -> None:
        """
        Validate business rules for devotee updates.

        Args:
            devotee_update: Update data
            existing_devotee: Existing devotee record

        Raises:
            ValueError: If validation fails
        """
        # Extract update data
        update_data = devotee_update.model_dump(exclude_unset=True)

        # Validate date consistency
        if "date_of_marriage" in update_data and update_data["date_of_marriage"]:
            marriage_date = update_data["date_of_marriage"]
            birth_date = (
                update_data.get("date_of_birth")
                if "date_of_birth" in update_data
                else existing_devotee.date_of_birth
            )
            if birth_date and marriage_date < birth_date:
                raise ValueError("Date of marriage cannot be before date of birth")

        if "initiation_date" in update_data and update_data["initiation_date"]:
            initiation_date = update_data["initiation_date"]
            birth_date = (
                update_data.get("date_of_birth")
                if "date_of_birth" in update_data
                else existing_devotee.date_of_birth
            )
            if birth_date and initiation_date < birth_date:
                raise ValueError("Initiation date cannot be before date of birth")

        if "chanting_16_rounds_since" in update_data and update_data["chanting_16_rounds_since"]:
            chanting_since = update_data["chanting_16_rounds_since"]
            birth_date = (
                update_data.get("date_of_birth")
                if "date_of_birth" in update_data
                else existing_devotee.date_of_birth
            )
            if birth_date and chanting_since < birth_date:
                raise ValueError("Chanting start date cannot be before date of birth")

        # Validate marital status consistency
        if "marital_status" in update_data:
            marital_status = update_data["marital_status"]
            if marital_status in [MaritalStatus.GRHASTA]:
                spouse_name = (
                    update_data.get("spouse_name")
                    if "spouse_name" in update_data
                    else existing_devotee.spouse_name
                )
                if not spouse_name:
                    logger.warning(
                        f"Devotee {existing_devotee.id} marked as GRHASTA but no spouse name provided"
                    )

        # Validate initiation requirements
        if "initiation_status" in update_data:
            initiation_status = update_data["initiation_status"]
            if initiation_status in [InitiationStatus.HARINAM, InitiationStatus.BRAHMIN]:
                spiritual_master = (
                    update_data.get("spiritual_master")
                    if "spiritual_master" in update_data
                    else existing_devotee.spiritual_master
                )
                if not spiritual_master:
                    raise ValueError(
                        f"Spiritual master is required for initiation status: {initiation_status.value}"
                    )

                initiation_date = (
                    update_data.get("initiation_date")
                    if "initiation_date" in update_data
                    else existing_devotee.initiation_date
                )
                if not initiation_date:
                    logger.warning(
                        f"Devotee {existing_devotee.id} has initiation status but no initiation date"
                    )

    def update_devotee(
        self,
        db: Session,
        devotee_id: int,
        devotee_update: DevoteeUpdate,
        photo: UploadFile | None = None,
    ) -> Devotee | None:
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
            storage_service = StorageService()

            # Delete old photo if exists
            if devotee.profile_photo_path:
                old_filename = Path(devotee.profile_photo_path).name
                storage_service.delete_file(devotee.id, old_filename)

            # Upload new photo
            photo_metadata = storage_service.upload_file(
                file=photo, user_id=devotee.id, file_purpose="profile_photo"
            )
            update_data["photo_path"] = photo_metadata["gcs_path"]

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
            db.query(func.count(Devotee.id)).filter(Devotee.created_at >= thirty_days_ago).scalar()
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
            db.query(Devotee.gender, func.count(Devotee.id)).group_by(Devotee.gender).all()
        )

        # Statistics by marital status
        by_marital_status = dict(
            db.query(Devotee.marital_status, func.count(Devotee.id))
            .group_by(Devotee.marital_status)
            .all()
        )

        # Average age calculation
        avg_age_query = db.query(
            func.avg(func.timestampdiff(text("YEAR"), Devotee.date_of_birth, func.curdate())).label(
                "avg_age"
            )
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
    ) -> list[Devotee]:
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
        country: str | None = None,
        state: str | None = None,
        city: str | None = None,
    ) -> list[Devotee]:
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

    def get_devotees_by_spiritual_master(self, db: Session, spiritual_master: str) -> list[Devotee]:
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
            self.db.query(Devotee).filter(Devotee.email == devotee_data.email.lower()).first()
        )

        if existing_devotee:
            if existing_devotee.email_verified is True:
                raise StandardHTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    message="A verified devotee with this email already exists",
                    success=False,
                    data=None,
                )
            # Resend verification email for unverified devotee
            await self._send_verification_email(existing_devotee)
            raise StandardHTTPException(
                status_code=status.HTTP_409_CONFLICT,
                message="Devotee exists but is not verified. Verification email sent again.",
                success=False,
                data=None,
            )

        # Generate secure verification token
        verification_token = secrets.token_urlsafe(32)
        verification_expires = datetime.now(UTC) + timedelta(hours=24)

        # Create new devotee with minimal information (unverified)
        new_devotee = Devotee(
            # Basic authentication fields
            email=devotee_data.email.lower(),
            password_hash=get_password_hash(devotee_data.password),
            # Minimal profile information
            legal_name=devotee_data.legal_name.strip(),
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

            logger.info(f"Created simple unverified devotee with email: {devotee_data.email}")
            return new_devotee

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create simple unverified devotee: {e!s}")
            raise StandardHTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to create devotee account",
                success=False,
                data=None,
            ) from None

    async def verify_devotee_email(self, token: str) -> str:
        """Verify devotee's email using verification token.

        Returns:
            str: The verified email address
        """
        devotee = self.db.query(Devotee).filter(Devotee.verification_token == token).first()

        if not devotee:
            raise StandardHTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Invalid or expired verification token",
                success=False,
                data=None,
            )

        # Check if already verified
        if getattr(devotee, "email_verified", False) is True:
            raise StandardHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Email is already verified",
                success=False,
                data=None,
            )

        # Check if token is expired with proper timezone handling
        if devotee.verification_expires is not None:
            current_time = datetime.now(UTC)
            expires_at = devotee.verification_expires

            # Handle timezone awareness - if tzinfo is None, assume UTC
            if hasattr(expires_at, "tzinfo") and expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)

            if expires_at < current_time:
                raise StandardHTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="Verification token has expired",
                    success=False,
                    data=None,
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
                email_service = GmailService()
                await email_service.send_email_verification_success(
                    verified_email, devotee.legal_name
                )
            except Exception as email_error:
                logger.warning(f"Failed to send verification success email: {email_error}")
                # Continue with verification even if email fails

            logger.info(f"Verified devotee email: {verified_email}")
            return verified_email

        except Exception as e:
            logger.error(f"Failed to verify devotee email: {e!s}")
            self.db.rollback()
            raise StandardHTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to verify email",
                success=False,
                data=None,
            ) from None

    async def resend_verification_email(self, email: str) -> bool:
        """Resend verification email to devotee."""
        devotee = self.get_devotee_by_email(self.db, email)
        if not devotee:
            raise StandardHTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Devotee not found",
                success=False,
                data=None,
            )

        # Check if already verified - ensure we get the actual boolean value
        already_verified = getattr(devotee, "email_verified", False)
        if already_verified is True:
            raise StandardHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Email is already verified",
                success=False,
                data=None,
            )

        try:
            # Generate new verification token
            devotee.verification_token = secrets.token_urlsafe(32)
            devotee.verification_expires = datetime.now(UTC) + timedelta(hours=24)

            await self._send_verification_email(devotee)

            self.db.commit()
            logger.info(f"Resent verification email to: {email}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to resend verification email: {e!s}")
            raise StandardHTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to resend verification email",
                success=False,
                data=None,
            )

    async def _send_verification_email(self, devotee: Devotee):
        """Send verification email to devotee."""
        email_service = GmailService()
        await email_service.send_email_verification(
            email=devotee.email,
            user_name=devotee.legal_name,
            verification_token=devotee.verification_token,
        )

    async def send_password_reset_email(self, email: str) -> bool:
        """Send password reset email to devotee."""
        devotee = self.get_devotee_by_email(self.db, email)
        if not devotee:
            raise StandardHTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="User not found",
                success=False,
                data=None,
            )

        if getattr(devotee, "email_verified", False) is not True:
            raise StandardHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Email must be verified before password reset",
                success=False,
                data=None,
            )

        try:
            # Generate reset token
            devotee.password_reset_token = secrets.token_urlsafe(32)
            devotee.password_reset_expires = datetime.now(UTC) + timedelta(hours=1)

            # Send reset email
            email_service = GmailService()
            await email_service.send_password_reset_email(
                email=devotee.email,
                reset_token=devotee.password_reset_token,
                user_name=devotee.legal_name,
            )

            self.db.commit()
            logger.info(f"Sent password reset email to: {email}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to send password reset email: {e!s}")
            raise StandardHTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to send password reset email",
                success=False,
                data=None,
            ) from None

    def reset_password_with_token(self, token: str, new_password: str) -> bool:
        """Reset devotee's password using reset token."""
        devotee = self.db.query(Devotee).filter(Devotee.password_reset_token == token).first()

        if not devotee:
            raise StandardHTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Invalid reset token",
                success=False,
                data=None,
            )

        # Check if token is expired
        # Convert to timezone-aware if needed (MySQL doesn't store timezone info)
        expires_time = devotee.password_reset_expires
        if expires_time.tzinfo is None:
            expires_time = expires_time.replace(tzinfo=UTC)

        if expires_time < datetime.now(UTC):
            raise StandardHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Reset token has expired",
                success=False,
                data=None,
            )

        try:
            # Update password and clear reset token
            devotee.password_hash = get_password_hash(new_password)
            devotee.password_reset_token = None
            devotee.password_reset_expires = None

            self.db.commit()
            logger.info(f"Password reset successful for devotee: {devotee.email}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to reset password: {e!s}")
            raise StandardHTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to reset password",
                success=False,
                data=None,
            ) from None

    def admin_reset_password(self, devotee_id: int, new_password: str, admin_id: int) -> bool:
        """Admin function to reset any devotee's password."""
        devotee = self.get_devotee_by_id(self.db, devotee_id)
        if not devotee:
            raise StandardHTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Devotee not found",
                success=False,
                data=None,
            )

        try:
            devotee.password_hash = get_password_hash(new_password)

            self.db.commit()
            logger.info(f"Admin {admin_id} reset password for devotee {devotee_id}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to admin reset password: {e!s}")
            raise StandardHTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to reset password",
                success=False,
                data=None,
            ) from None

    def authenticate_devotee(self, email: str, password: str) -> Devotee | None:
        """Authenticate devotee with email and password."""
        devotee = self.get_devotee_by_email(self.db, email)
        if not devotee:
            return None

        if getattr(devotee, "email_verified", False) is not True:
            raise StandardHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Email must be verified before login",
                success=False,
                data=None,
            )

        if not verify_password(password, devotee.password_hash):
            return None

        return devotee

    def _validate_total_file_size(self, devotee: Devotee, new_file_size: int) -> None:
        """
        Validate that adding a new file won't exceed total size limit.

        Args:
            devotee: Devotee object
            new_file_size: Size of new file in bytes

        Raises:
            HTTPException: If total size would exceed limit
        """
        total_size = new_file_size

        # Add size of existing uploaded files
        if devotee.uploaded_files:
            for file_info in devotee.uploaded_files:
                total_size += file_info.get("size", 0)

        # Check against limit
        if total_size > settings.max_upload_size_bytes:
            raise StandardHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=f"Total file size ({total_size / 1024 / 1024:.2f}MB) would exceed maximum allowed ({settings.max_upload_size_mb}MB). Please delete some files first.",
                success=False,
                data=None,
            )

    async def complete_devotee_profile(
        self,
        user_id: int,
        profile_data: dict,
        profile_photo: UploadFile | None = None,
        uploaded_files: list[UploadFile] | None = None,
    ) -> Devotee:
        """
        Complete devotee profile after email verification with file uploads.

        Args:
            user_id: Devotee's user ID
            profile_data: Dictionary of profile fields to update
            profile_photo: Optional profile photo
            uploaded_files: Optional list of document files (max 5)

        Returns:
            Devotee: The updated devotee object

        Raises:
            HTTPException: For validation errors or save failures
        """
        devotee = self.get_devotee_by_id(self.db, user_id)
        if not devotee:
            raise StandardHTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Devotee not found",
                success=False,
                data=None,
            )

        # Check if email is verified
        if getattr(devotee, "email_verified", False) is not True:
            raise StandardHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Email must be verified before completing profile",
                success=False,
                data=None,
            )

        try:
            # Update devotee with profile data (excluding file fields)
            for field, value in profile_data.items():
                if hasattr(devotee, field) and field not in [
                    "profile_photo_path",
                    "uploaded_files",
                ]:
                    setattr(devotee, field, value)

            # Handle profile photo upload
            if profile_photo:
                storage_service = StorageService()
                photo_metadata = storage_service.upload_file(
                    file=profile_photo, user_id=user_id, file_purpose="profile_photo"
                )
                devotee.profile_photo_path = photo_metadata["gcs_path"]
                logger.info(f"Saved profile photo for user {user_id}")

            # Handle document uploads
            if uploaded_files:
                # Validate file count
                existing_files = devotee.uploaded_files or []
                total_files = len(existing_files) + len(uploaded_files)

                if total_files > settings.max_files_per_user:
                    raise StandardHTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        message=f"Maximum {settings.max_files_per_user} files allowed. You have {
                            len(existing_files)
                        } existing files.",
                    )

                # Save each file and collect metadata
                storage_service = StorageService()
                new_files_metadata = []
                for idx, uploaded_file in enumerate(uploaded_files, 1):
                    # Validate total size before saving
                    uploaded_file.file.seek(0, 2)
                    file_size = uploaded_file.file.tell()
                    uploaded_file.file.seek(0)

                    self._validate_total_file_size(devotee, file_size)

                    # Extract purpose from filename or use default
                    purpose = (
                        Path(uploaded_file.filename).stem
                        if uploaded_file.filename
                        else f"document_{idx}"
                    )

                    # Save file to GCS
                    file_metadata = storage_service.upload_file(
                        file=uploaded_file, user_id=user_id, file_purpose=purpose
                    )
                    new_files_metadata.append(file_metadata)

                # Update devotee's uploaded_files array
                devotee.uploaded_files = existing_files + new_files_metadata
                logger.info(f"Saved {len(new_files_metadata)} document(s) for user {user_id}")

            self.db.commit()
            self.db.refresh(devotee)
            logger.info(f"Completed profile for devotee: {devotee.email}")
            return devotee

        except HTTPException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to complete devotee profile: {e!s}")
            raise StandardHTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to complete profile",
                success=False,
                data=None,
            ) from None


# Note: Global service instance removed due to db session requirement
# Use DevoteeService(db) in each endpoint instead
