"""
Business logic service for yatra registration management.

This service handles registration CRUD operations with comprehensive validation,
status transitions, and payment handling.
"""

import logging
from datetime import UTC, date, datetime

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.yatra_validators import (
    validate_registration_capacity,
    validate_registration_dates,
    validate_status_transition,
)
from app.db.models import RegistrationStatus, YatraRegistration, YatraStatus
from app.repositories.registration_repository import RegistrationRepository
from app.repositories.yatra_repository import YatraRepository
from app.schemas.yatra_registration import RegistrationCreate, RegistrationUpdate
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)

# Status transition rules
STATUS_TRANSITIONS = {
    RegistrationStatus.PENDING: [
        RegistrationStatus.PAYMENT_SUBMITTED,
        RegistrationStatus.CANCELLED_BY_USER,
        RegistrationStatus.CANCELLED_BY_ADMIN,
    ],
    RegistrationStatus.PAYMENT_SUBMITTED: [
        RegistrationStatus.PAYMENT_VERIFIED,
        RegistrationStatus.PENDING,
        RegistrationStatus.CANCELLED_BY_ADMIN,
    ],
    RegistrationStatus.PAYMENT_VERIFIED: [
        RegistrationStatus.CONFIRMED,
        RegistrationStatus.CANCELLED_BY_ADMIN,
    ],
    RegistrationStatus.CONFIRMED: [
        RegistrationStatus.COMPLETED,
        RegistrationStatus.CANCELLED_BY_ADMIN,
    ],
}


class YatraRegistrationService:
    """Service for yatra registration business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.repository = RegistrationRepository(db)
        self.yatra_repository = YatraRepository(db)
        self.storage_service = StorageService()

    @validate_registration_dates
    @validate_registration_capacity
    def create_registration(
        self, devotee_id: int, reg_data: RegistrationCreate
    ) -> YatraRegistration:
        """Create new registration with comprehensive validation."""
        try:
            # Validate yatra exists and is accepting registrations
            yatra = self.yatra_repository.get_by_id(reg_data.yatra_id)
            if not yatra:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Yatra not found")

            # Check registration is open
            today = date.today()
            if today < yatra.registration_start_date:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Registration opens on {yatra.registration_start_date}",
                )

            if today > yatra.registration_deadline:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Registration deadline has passed",
                )

            if yatra.status not in [YatraStatus.UPCOMING, YatraStatus.DRAFT]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Yatra is {yatra.status.value} and not accepting registrations",
                )

            # Check for duplicate registration
            if self.repository.check_duplicate_registration(reg_data.yatra_id, devotee_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You already have an active registration for this yatra",
                )

            # Validate travel dates within yatra period
            if reg_data.arrival_datetime.date() < yatra.start_date:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Arrival date cannot be before yatra start date",
                )

            if reg_data.departure_datetime.date() > yatra.end_date:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Departure date cannot be after yatra end date",
                )

            # Calculate total amount
            total_amount = reg_data.number_of_members * yatra.price_per_person

            # Create registration
            reg_dict = reg_data.model_dump(mode="json")  # Use mode="json" to serialize dates/enums
            reg_dict["devotee_id"] = devotee_id
            reg_dict["total_amount"] = total_amount
            reg_dict["status"] = RegistrationStatus.PENDING
            reg_dict["submitted_at"] = datetime.now(UTC)

            registration = self.repository.create(reg_dict)
            self.db.commit()

            logger.info(
                f"Registration created: {registration.registration_number} for yatra {yatra.id}"
            )
            return registration

        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create registration: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create registration",
            )

    async def upload_payment_screenshot(
        self,
        reg_id: int,
        devotee_id: int,
        file: UploadFile,
        payment_reference: str | None = None,
    ) -> YatraRegistration:
        """Upload payment screenshot and transition status."""
        try:
            registration = self.repository.get_by_id(reg_id)
            if not registration:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Registration not found",
                )

            # Check ownership
            if registration.devotee_id != devotee_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only upload payment for your own registration",
                )

            # Validate status
            if registration.status != RegistrationStatus.PENDING:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot upload payment for registration in {registration.status.value} status",
                )

            # Upload to GCS
            file_metadata = self.storage_service.upload_file(
                file=file,
                user_id=devotee_id,
                file_purpose=f"yatra_payment_{registration.registration_number}",
            )

            # Update registration
            registration.payment_screenshot_path = file_metadata["gcs_path"]
            registration.payment_reference = payment_reference
            registration.payment_date = datetime.now(UTC)

            # Transition status
            registration = self.repository.update_status(
                registration=registration,
                new_status=RegistrationStatus.PAYMENT_SUBMITTED,
                admin_id=None,
                remarks="Payment screenshot uploaded by devotee",
            )

            self.db.commit()

            logger.info(f"Payment uploaded for registration {registration.registration_number}")
            return registration

        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to upload payment: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload payment screenshot",
            )

    def get_registration(self, reg_id: int, user_id: int, is_admin: bool) -> YatraRegistration:
        """Get registration details with access control."""
        registration = self.repository.get_by_id(reg_id)
        if not registration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found"
            )

        # Check access
        if not is_admin and registration.devotee_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only access your own registrations",
            )

        return registration

    def update_registration(
        self, reg_id: int, devotee_id: int, update_data: RegistrationUpdate
    ) -> YatraRegistration:
        """Update registration details (only if PENDING)."""
        try:
            registration = self.repository.get_by_id(reg_id)
            if not registration:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Registration not found",
                )

            # Check ownership
            if registration.devotee_id != devotee_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only update your own registration",
                )

            # Only allow updates in PENDING status
            if registration.status != RegistrationStatus.PENDING:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot update registration in {registration.status.value} status",
                )

            update_dict = update_data.model_dump(exclude_unset=True)
            for key, value in update_dict.items():
                if hasattr(registration, key):
                    setattr(registration, key, value)

            self.db.commit()

            logger.info(f"Registration {registration.registration_number} updated")
            return registration

        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update registration: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update registration",
            )

    @validate_status_transition(STATUS_TRANSITIONS)
    def update_registration_status(
        self,
        reg_id: int,
        new_status: RegistrationStatus,
        admin_id: int,
        admin_remarks: str | None = None,
        current_status: RegistrationStatus | None = None,
    ) -> YatraRegistration:
        """Update registration status (admin only) with state machine validation."""
        try:
            registration = self.repository.get_by_id(reg_id)
            if not registration:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Registration not found",
                )

            # Set current_status for decorator validation
            if current_status is None:
                current_status = registration.status

            registration = self.repository.update_status(
                registration=registration,
                new_status=new_status,
                admin_id=admin_id,
                remarks=admin_remarks,
            )

            if new_status == RegistrationStatus.CONFIRMED:
                registration.confirmed_by = admin_id
                registration.confirmed_at = datetime.now(UTC)

            if admin_remarks:
                registration.admin_remarks = admin_remarks

            self.db.commit()

            logger.info(
                f"Registration {registration.registration_number} status updated to "
                f"{new_status.value} by admin {admin_id}"
            )
            return registration

        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update registration status: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update registration status",
            )

    def cancel_registration(
        self, reg_id: int, devotee_id: int, cancellation_reason: str | None = None
    ) -> YatraRegistration:
        """Cancel registration (user action)."""
        try:
            registration = self.repository.get_by_id(reg_id)
            if not registration:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Registration not found",
                )

            # Check ownership
            if registration.devotee_id != devotee_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only cancel your own registration",
                )

            # Only allow cancellation for PENDING or PAYMENT_SUBMITTED
            if registration.status not in [
                RegistrationStatus.PENDING,
                RegistrationStatus.PAYMENT_SUBMITTED,
            ]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot cancel registration in {registration.status.value} status. Please contact admin.",
                )

            registration = self.repository.update_status(
                registration=registration,
                new_status=RegistrationStatus.CANCELLED_BY_USER,
                admin_id=None,
                remarks=cancellation_reason or "Cancelled by devotee",
            )

            self.db.commit()

            logger.info(f"Registration {registration.registration_number} cancelled by devotee")
            return registration

        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to cancel registration: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to cancel registration",
            )

    def list_devotee_registrations(
        self, devotee_id: int, status_filter: RegistrationStatus | None = None
    ) -> list[YatraRegistration]:
        """List all registrations for a devotee."""
        return self.repository.list_by_devotee(devotee_id, status=status_filter)

    def list_yatra_registrations(
        self, yatra_id: int, status_filter: RegistrationStatus | None = None
    ) -> list[YatraRegistration]:
        """List all registrations for a yatra (admin only)."""
        return self.repository.list_by_yatra(yatra_id, status=status_filter)
