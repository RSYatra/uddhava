"""
Business logic service for yatra registration management.

This service handles group registrations with individual member tracking,
pricing calculation, and payment management.
"""

import logging
from datetime import UTC, date, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import (
    PaymentOption,
    PricingTemplateDetail,
    RegistrationStatus,
    Yatra,
    YatraMember,
    YatraPaymentOption,
    YatraRegistration,
    YatraStatus,
)
from app.repositories.yatra_repository import YatraRepository
from app.schemas.yatra_registration import RegistrationCreate
from app.utils.yatra_helpers import (
    calculate_member_price,
    generate_group_id,
    generate_registration_number,
    validate_member_dates,
)

logger = logging.getLogger(__name__)


class YatraRegistrationService:
    """Service for yatra registration business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.yatra_repository = YatraRepository(db)

    def create_registration(self, devotee_id: int, reg_data: RegistrationCreate) -> dict:
        """
        Create new group registration with individual member tracking.

        Args:
            devotee_id: ID of the devotee creating the registration
            reg_data: Registration data with members array

        Returns:
            Dictionary with group_id, registrations, members, total_amount, payment_options

        Raises:
            HTTPException: For validation errors or system failures
        """
        try:
            # Validate yatra exists and is accepting registrations
            yatra = self.yatra_repository.get_by_id(reg_data.yatra_id)
            if not yatra:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Yatra not found")

            self._validate_registration_open(yatra)

            # Get pricing template details
            pricing_details = (
                self.db.query(PricingTemplateDetail)
                .filter(PricingTemplateDetail.template_id == yatra.pricing_template_id)
                .all()
            )

            if not pricing_details:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Pricing template not configured for this yatra",
                )

            # Validate all members
            for member in reg_data.members:
                validate_member_dates(member, yatra.start_date, yatra.end_date)

            # Generate group ID
            group_id = generate_group_id()

            # Get next registration sequence number
            sequence = self._get_next_sequence(reg_data.yatra_id)

            # Create registrations and members
            registrations = []
            members = []
            total_amount = 0

            for idx, member_data in enumerate(reg_data.members):
                # Calculate price for this member
                price_charged, is_free = calculate_member_price(member_data, pricing_details)
                total_amount += price_charged

                # Create registration record
                registration_number = generate_registration_number(
                    reg_data.yatra_id, sequence + idx
                )

                registration = YatraRegistration(
                    registration_number=registration_number,
                    yatra_id=reg_data.yatra_id,
                    devotee_id=devotee_id,
                    group_id=group_id,
                    is_group_lead=member_data.is_primary_registrant,
                    total_amount=price_charged,  # Individual member amount
                    status=RegistrationStatus.PENDING,
                    submitted_at=datetime.now(UTC),
                )
                self.db.add(registration)
                self.db.flush()

                # Create member record
                member = YatraMember(
                    registration_id=registration.id,
                    devotee_id=member_data.devotee_id,
                    legal_name=member_data.legal_name,
                    gender=member_data.gender,
                    date_of_birth=member_data.date_of_birth,
                    mobile_number=member_data.mobile_number,
                    email=member_data.email,
                    arrival_datetime=member_data.arrival_datetime,
                    departure_datetime=member_data.departure_datetime,
                    room_category=member_data.room_category,
                    price_charged=price_charged,
                    is_free=is_free,
                    is_primary_registrant=member_data.is_primary_registrant,
                    is_registered_user=member_data.devotee_id is not None,
                    dietary_requirements=member_data.dietary_requirements,
                    medical_conditions=member_data.medical_conditions,
                )
                self.db.add(member)

                registrations.append(registration)
                members.append(member)

            # Get payment options for the yatra
            payment_options = (
                self.db.query(PaymentOption)
                .join(YatraPaymentOption)
                .filter(YatraPaymentOption.yatra_id == reg_data.yatra_id)
                .order_by(YatraPaymentOption.display_order)
                .all()
            )

            self.db.commit()

            logger.info(
                f"Group registration created: {group_id} for yatra {reg_data.yatra_id} "
                f"with {len(members)} members, total amount: {total_amount}"
            )

            return {
                "group_id": group_id,
                "registrations": registrations,
                "members": members,
                "total_amount": total_amount,
                "payment_options": payment_options,
            }

        except HTTPException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create registration: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create registration: {str(e)}",
            )

    def get_registration_by_id(self, reg_id: int, devotee_id: int) -> dict:
        """Get registration with member details."""
        registration = (
            self.db.query(YatraRegistration)
            .filter(
                YatraRegistration.id == reg_id,
                YatraRegistration.devotee_id == devotee_id,
                YatraRegistration.deleted_at.is_(None),
            )
            .first()
        )

        if not registration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found"
            )

        # Get all members for this registration
        members = self.db.query(YatraMember).filter(YatraMember.registration_id == reg_id).all()

        return {"registration": registration, "members": members}

    def get_group_registrations(self, group_id: str, devotee_id: int) -> dict:
        """Get all registrations and members for a group."""
        registrations = (
            self.db.query(YatraRegistration)
            .filter(
                YatraRegistration.group_id == group_id,
                YatraRegistration.devotee_id == devotee_id,
                YatraRegistration.deleted_at.is_(None),
            )
            .all()
        )

        if not registrations:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No registrations found for this group",
            )

        # Get all members for these registrations
        reg_ids = [r.id for r in registrations]
        members = self.db.query(YatraMember).filter(YatraMember.registration_id.in_(reg_ids)).all()

        total_amount = sum(r.total_amount for r in registrations)

        return {
            "group_id": group_id,
            "registrations": registrations,
            "members": members,
            "total_amount": total_amount,
        }

    def _validate_registration_open(self, yatra: Yatra) -> None:
        """Validate that registration is currently open for the yatra."""
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

    def _get_next_sequence(self, yatra_id: int) -> int:
        """Get the next registration sequence number for a yatra."""
        count = (
            self.db.query(YatraRegistration).filter(YatraRegistration.yatra_id == yatra_id).count()
        )
        return count + 1
