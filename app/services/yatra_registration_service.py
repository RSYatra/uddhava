"""
Business logic service for yatra registration management.

This service handles group registrations with individual member tracking,
pricing calculation based on room categories, and payment management.
"""

import logging
from datetime import date
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.responses import StandardHTTPException
from app.db.models import (
    Gender,
    PaymentOption,
    PaymentStatus,
    RegistrationStatus,
    RoomPreference,
    Yatra,
    YatraMember,
    YatraPaymentOption,
    YatraRegistration,
)
from app.schemas.yatra_registration import RegistrationCreate, RegistrationUpdate
from app.utils.yatra_helpers import (
    calculate_member_price,
    generate_group_id,
    validate_payment_option_for_yatra,
    validate_room_category_exists_in_template,
)

logger = logging.getLogger(__name__)


class YatraRegistrationService:
    """Service for yatra registration business logic."""

    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db

    def create_registration(self, devotee_id: int, reg_data: RegistrationCreate) -> dict:
        """
        Create new group registration with individual member tracking.

        Args:
            devotee_id: ID of the devotee creating the registration
            reg_data: Registration data with members array and payment option

        Returns:
            Dictionary with group_id, registration, members, total_amount, payment_options

        Raises:
            HTTPException: For validation errors or system failures
        """
        try:
            # Validate yatra exists and is accepting registrations
            yatra = self.db.query(Yatra).filter(Yatra.id == reg_data.yatra_id).first()
            if not yatra:
                raise StandardHTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message="Yatra not found",
                    success=False,
                    data=None,
                )

            self._validate_registration_open(yatra)

            # Validate payment option is available for this yatra
            if not validate_payment_option_for_yatra(
                reg_data.yatra_id, reg_data.payment_option_id, self.db
            ):
                raise StandardHTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="Selected payment option is not available for this yatra",
                    success=False,
                    data=None,
                )

            # Validate all room categories exist
            for member in reg_data.members:
                if not validate_room_category_exists_in_template(
                    reg_data.yatra_id, member.room_category, self.db
                ):
                    raise StandardHTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        message=f"Room category '{member.room_category}' not found for this yatra",
                        success=False,
                        data=None,
                    )

            # Generate group ID
            group_id = generate_group_id(reg_data.yatra_id, yatra.start_date, self.db)

            # Calculate prices for all members
            total_amount = Decimal("0")
            member_prices = []

            for member_data in reg_data.members:
                price = calculate_member_price(
                    member_data.date_of_birth,
                    yatra.start_date,
                    reg_data.yatra_id,
                    member_data.room_category,
                    self.db,
                )
                member_prices.append(int(price))
                total_amount += price

            # Find the primary registrant
            primary_member = next(m for m in reg_data.members if m.is_primary_registrant)

            # Verify primary registrant is the current devotee
            if primary_member.devotee_id != devotee_id:
                raise StandardHTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="Primary registrant must be the current user",
                    success=False,
                    data=None,
                )

            # Create single registration record (for the group lead)
            registration = YatraRegistration(
                yatra_id=reg_data.yatra_id,
                devotee_id=devotee_id,
                group_id=group_id,
                is_group_lead=True,
                payment_option_id=reg_data.payment_option_id,
                payment_amount=int(total_amount),
                payment_status=PaymentStatus.PENDING,
                status=RegistrationStatus.PENDING,
            )
            self.db.add(registration)
            self.db.flush()

            # Create member records
            members = []
            for idx, member_data in enumerate(reg_data.members):
                # Convert string values to enums
                # For Gender, map string to enum value
                gender_map = {"M": Gender.MALE, "F": Gender.FEMALE}
                gender_enum = gender_map.get(member_data.gender, Gender.MALE)

                # For RoomPreference, use enum name lookup
                room_pref_enum = RoomPreference[member_data.room_preference]

                member = YatraMember(
                    registration_id=registration.id,
                    devotee_id=member_data.devotee_id,
                    legal_name=member_data.legal_name,
                    date_of_birth=member_data.date_of_birth,
                    gender=gender_enum,
                    mobile_number=member_data.mobile_number,
                    email=member_data.email,
                    room_category=member_data.room_category,
                    room_preference=room_pref_enum,
                    is_primary_registrant=member_data.is_primary_registrant,
                    price_charged=member_prices[idx],
                    arrival_datetime=member_data.arrival_datetime,
                    departure_datetime=member_data.departure_datetime,
                    dietary_requirements=member_data.dietary_requirements,
                    medical_conditions=member_data.medical_conditions,
                )
                self.db.add(member)
                members.append(member)

            # Get payment options for the yatra
            payment_options = (
                self.db.query(PaymentOption)
                .join(YatraPaymentOption)
                .filter(YatraPaymentOption.yatra_id == reg_data.yatra_id)
                .all()
            )

            self.db.commit()

            logger.info(
                f"Group registration created: {group_id} for yatra {reg_data.yatra_id} "
                f"with {len(members)} members, total amount: {total_amount}"
            )

            return {
                "group_id": group_id,
                "registration": registration,
                "members": members,
                "total_amount": int(total_amount),
                "payment_options": payment_options,
            }

        except HTTPException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create registration: {e}")
            raise StandardHTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Failed to create registration: {str(e)}",
            )

    def _get_registration_by_id_internal(self, reg_id: int) -> dict:
        """
        Internal method to get registration without authorization check.

        Args:
            reg_id: Registration ID

        Returns:
            Dictionary with registration and members

        Raises:
            HTTPException: If registration not found
        """
        registration = (
            self.db.query(YatraRegistration).filter(YatraRegistration.id == reg_id).first()
        )

        if not registration:
            raise StandardHTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Registration not found",
                success=False,
                data=None,
            )

        # Get all members for this registration
        members = self.db.query(YatraMember).filter(YatraMember.registration_id == reg_id).all()

        return {"registration": registration, "members": members}

    def get_registration_by_id(self, reg_id: int, devotee_id: int) -> dict:
        """
        Get registration with member details.

        Args:
            reg_id: Registration ID
            devotee_id: ID of the devotee requesting the registration (for access control)

        Returns:
            Dictionary with registration and members

        Raises:
            HTTPException: If registration not found or access denied
        """
        result = self._get_registration_by_id_internal(reg_id)
        registration = result["registration"]

        # Verify access - only the devotee who created the registration can view it
        if registration.devotee_id != devotee_id:
            raise StandardHTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                message="You do not have permission to view this registration",
                success=False,
                data=None,
            )

        return result

    def get_registrations_for_devotee(self, devotee_id: int) -> list[dict]:
        """
        Get all registrations for a devotee.

        Args:
            devotee_id: Devotee ID

        Returns:
            List of registration dictionaries with members
        """
        registrations = (
            self.db.query(YatraRegistration)
            .filter(YatraRegistration.devotee_id == devotee_id)
            .all()
        )

        result = []
        for reg in registrations:
            members = self.db.query(YatraMember).filter(YatraMember.registration_id == reg.id).all()
            result.append({"registration": reg, "members": members})

        return result

    def get_registrations_for_yatra(self, yatra_id: int) -> list[dict]:
        """
        Get all registrations for a yatra (admin only).

        Args:
            yatra_id: Yatra ID

        Returns:
            List of registration dictionaries with members
        """
        registrations = (
            self.db.query(YatraRegistration).filter(YatraRegistration.yatra_id == yatra_id).all()
        )

        result = []
        for reg in registrations:
            members = self.db.query(YatraMember).filter(YatraMember.registration_id == reg.id).all()
            result.append({"registration": reg, "members": members})

        return result

    def get_group_registrations(self, group_id: str, devotee_id: int) -> dict:
        """
        Get all registrations and members for a group.

        Args:
            group_id: Group ID
            devotee_id: ID of the devotee requesting the group (for access control)

        Returns:
            Dictionary with group details

        Raises:
            HTTPException: If group not found or access denied
        """
        registrations = (
            self.db.query(YatraRegistration).filter(YatraRegistration.group_id == group_id).all()
        )

        if not registrations:
            raise StandardHTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="No registrations found for this group",
                success=False,
                data=None,
            )

        # Verify access - only the devotee who created the registration can view it
        if registrations[0].devotee_id != devotee_id:
            raise StandardHTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                message="You do not have permission to view this group",
                success=False,
                data=None,
            )

        # Get all members for these registrations
        reg_ids = [r.id for r in registrations]
        members = self.db.query(YatraMember).filter(YatraMember.registration_id.in_(reg_ids)).all()

        # Get yatra details
        yatra = self.db.query(Yatra).filter(Yatra.id == registrations[0].yatra_id).first()

        total_amount = sum(r.payment_amount for r in registrations)

        return {
            "group_id": group_id,
            "yatra_id": yatra.id if yatra else None,
            "yatra_name": yatra.name if yatra else None,
            "registrations": registrations,
            "members": members,
            "total_amount": total_amount,
            "payment_status": registrations[0].payment_status,
            "status": registrations[0].status,
        }

    def update_registration(
        self, reg_id: int, devotee_id: int, update_data: RegistrationUpdate
    ) -> dict:
        """
        Update registration details.

        Args:
            reg_id: Registration ID
            devotee_id: Devotee ID (for authorization)
            update_data: Update data

        Returns:
            Updated registration with members

        Raises:
            HTTPException: If registration not found or unauthorized
        """
        registration = (
            self.db.query(YatraRegistration)
            .filter(
                YatraRegistration.id == reg_id,
                YatraRegistration.devotee_id == devotee_id,
            )
            .first()
        )

        if not registration:
            raise StandardHTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Registration not found",
                success=False,
                data=None,
            )

        # Update fields
        if update_data.status is not None:
            registration.status = update_data.status
        if update_data.payment_status is not None:
            registration.payment_status = update_data.payment_status

        self.db.commit()
        self.db.refresh(registration)

        return self._get_registration_by_id_internal(reg_id)

    def update_registration_status(self, reg_id: int, new_status: RegistrationStatus) -> dict:
        """
        Update registration status (admin only).

        Args:
            reg_id: Registration ID
            new_status: New status

        Returns:
            Updated registration with members

        Raises:
            HTTPException: If registration not found
        """
        registration = (
            self.db.query(YatraRegistration).filter(YatraRegistration.id == reg_id).first()
        )

        if not registration:
            raise StandardHTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Registration not found",
                success=False,
                data=None,
            )

        registration.status = new_status
        self.db.commit()
        self.db.refresh(registration)

        return self._get_registration_by_id_internal(reg_id)

    def delete_registration(self, reg_id: int, devotee_id: int) -> None:
        """
        Delete a registration (only if in PENDING status).

        Args:
            reg_id: Registration ID
            devotee_id: Devotee ID (for authorization)

        Raises:
            HTTPException: If registration not found, unauthorized, or cannot be deleted
        """
        registration = (
            self.db.query(YatraRegistration)
            .filter(
                YatraRegistration.id == reg_id,
                YatraRegistration.devotee_id == devotee_id,
            )
            .first()
        )

        if not registration:
            raise StandardHTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Registration not found",
                success=False,
                data=None,
            )

        if registration.status != RegistrationStatus.PENDING:
            raise StandardHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Can only delete registrations in PENDING status",
                success=False,
                data=None,
            )

        # Delete members first (cascade should handle this, but being explicit)
        self.db.query(YatraMember).filter(YatraMember.registration_id == reg_id).delete()

        # Delete registration
        self.db.delete(registration)
        self.db.commit()

        logger.info(f"Registration {reg_id} deleted by devotee {devotee_id}")

    def _validate_registration_open(self, yatra: Yatra) -> None:
        """
        Validate that registration is currently open for the yatra.

        Args:
            yatra: Yatra object

        Raises:
            HTTPException: If registration is not open
        """
        today = date.today()

        if today > yatra.registration_deadline:
            raise StandardHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Registration deadline has passed",
                success=False,
                data=None,
            )

        if not yatra.is_active:
            raise StandardHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Yatra is not active and not accepting registrations",
                success=False,
                data=None,
            )
