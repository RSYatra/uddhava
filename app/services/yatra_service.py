"""
Business logic service for yatra management.

This service handles yatra CRUD operations with validation and transaction management.
"""

import logging
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import (
    PaymentOption,
    RegistrationStatus,
    RoomCategory,
    Yatra,
    YatraPaymentOption,
    YatraRegistration,
)
from app.schemas.yatra import YatraCreate, YatraUpdate

logger = logging.getLogger(__name__)


class YatraService:
    """Service for yatra business logic."""

    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db

    def create_yatra(self, yatra_data: YatraCreate) -> Yatra:
        """
        Create new yatra with validation.

        Args:
            yatra_data: Yatra creation data

        Returns:
            Created yatra

        Raises:
            HTTPException: For validation errors
        """
        try:
            # Create yatra
            yatra = Yatra(
                name=yatra_data.name,
                destination=yatra_data.destination,
                description=yatra_data.description,
                start_date=yatra_data.start_date,
                end_date=yatra_data.end_date,
                registration_deadline=yatra_data.registration_deadline,
                itinerary=yatra_data.itinerary,
                terms_and_conditions=yatra_data.terms_and_conditions,
                is_active=True,
            )

            self.db.add(yatra)
            self.db.commit()
            self.db.refresh(yatra)

            logger.info(f"Yatra created: {yatra.id}")
            return yatra

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create yatra: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create yatra",
            )

    def get_yatra(self, yatra_id: int) -> Yatra:
        """
        Get yatra by ID.

        Args:
            yatra_id: Yatra ID

        Returns:
            Yatra object

        Raises:
            HTTPException: If yatra not found
        """
        yatra = self.db.query(Yatra).filter(Yatra.id == yatra_id).first()

        if not yatra:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Yatra not found",
            )

        return yatra

    def get_yatra_with_details(self, yatra_id: int) -> dict:
        """
        Get yatra with room categories and payment options.

        Args:
            yatra_id: Yatra ID

        Returns:
            Dictionary with yatra, room_categories, and payment_options

        Raises:
            HTTPException: If yatra not found
        """
        yatra = self.get_yatra(yatra_id)

        # Get room categories
        room_categories = (
            self.db.query(RoomCategory)
            .filter(
                RoomCategory.yatra_id == yatra_id,
                RoomCategory.is_active,
            )
            .order_by(RoomCategory.price_per_person)
            .all()
        )

        # Get payment options
        payment_options = (
            self.db.query(PaymentOption)
            .join(YatraPaymentOption)
            .filter(YatraPaymentOption.yatra_id == yatra_id)
            .all()
        )

        return {
            "yatra": yatra,
            "room_categories": room_categories,
            "payment_options": payment_options,
        }

    def list_yatras(
        self,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = True,
    ) -> list[Yatra]:
        """
        List yatras with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            active_only: Only return active yatras

        Returns:
            List of yatras
        """
        query = self.db.query(Yatra)

        if active_only:
            query = query.filter(Yatra.is_active)

        return query.order_by(Yatra.start_date.desc()).offset(skip).limit(limit).all()

    def update_yatra(self, yatra_id: int, yatra_data: YatraUpdate) -> Yatra:
        """
        Update yatra details.

        Args:
            yatra_id: Yatra ID
            yatra_data: Update data

        Returns:
            Updated yatra

        Raises:
            HTTPException: If yatra not found or validation fails
        """
        yatra = self.get_yatra(yatra_id)

        # Check if yatra has already started
        if yatra.start_date <= date.today():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot update yatra that has already started",
            )

        try:
            # Update fields
            if yatra_data.name is not None:
                yatra.name = yatra_data.name
            if yatra_data.destination is not None:
                yatra.destination = yatra_data.destination
            if yatra_data.description is not None:
                yatra.description = yatra_data.description
            if yatra_data.start_date is not None:
                yatra.start_date = yatra_data.start_date
            if yatra_data.end_date is not None:
                yatra.end_date = yatra_data.end_date
            if yatra_data.registration_deadline is not None:
                yatra.registration_deadline = yatra_data.registration_deadline
            if yatra_data.itinerary is not None:
                yatra.itinerary = yatra_data.itinerary
            if yatra_data.terms_and_conditions is not None:
                yatra.terms_and_conditions = yatra_data.terms_and_conditions
            if yatra_data.is_active is not None:
                yatra.is_active = yatra_data.is_active

            self.db.commit()
            self.db.refresh(yatra)

            logger.info(f"Yatra updated: {yatra_id}")
            return yatra

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update yatra: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update yatra",
            )

    def delete_yatra(self, yatra_id: int) -> None:
        """
        Delete a yatra (only if no registrations exist).

        Args:
            yatra_id: Yatra ID

        Raises:
            HTTPException: If yatra not found or has registrations
        """
        yatra = self.get_yatra(yatra_id)

        # Check if yatra has any registrations
        registration_count = (
            self.db.query(YatraRegistration).filter(YatraRegistration.yatra_id == yatra_id).count()
        )

        if registration_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete yatra with existing registrations",
            )

        try:
            # Delete room categories (cascade will handle this)
            self.db.query(RoomCategory).filter(RoomCategory.yatra_id == yatra_id).delete()

            # Delete payment option associations
            self.db.query(YatraPaymentOption).filter(
                YatraPaymentOption.yatra_id == yatra_id
            ).delete()

            # Delete yatra
            self.db.delete(yatra)
            self.db.commit()

            logger.info(f"Yatra deleted: {yatra_id}")

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete yatra: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete yatra",
            )

    def get_registration_stats(self, yatra_id: int) -> dict:
        """
        Get registration statistics for a yatra.

        Args:
            yatra_id: Yatra ID

        Returns:
            Dictionary with registration stats
        """
        # Total registrations
        total = (
            self.db.query(YatraRegistration).filter(YatraRegistration.yatra_id == yatra_id).count()
        )

        # By status
        pending = (
            self.db.query(YatraRegistration)
            .filter(
                YatraRegistration.yatra_id == yatra_id,
                YatraRegistration.status == RegistrationStatus.PENDING,
            )
            .count()
        )

        confirmed = (
            self.db.query(YatraRegistration)
            .filter(
                YatraRegistration.yatra_id == yatra_id,
                YatraRegistration.status == RegistrationStatus.CONFIRMED,
            )
            .count()
        )

        return {
            "total_registrations": total,
            "pending": pending,
            "confirmed": confirmed,
        }

    def get_payment_options_with_aggregation(self, yatra_id: int) -> dict:
        """
        Get payment options for a yatra with aggregated metadata.

        Args:
            yatra_id: Yatra ID

        Returns:
            Dictionary with yatra info, payment options, and aggregated summary
        """
        yatra = self.get_yatra(yatra_id)

        # Get payment options
        payment_options = (
            self.db.query(PaymentOption)
            .join(YatraPaymentOption)
            .filter(
                YatraPaymentOption.yatra_id == yatra_id,
                PaymentOption.is_active,
            )
            .all()
        )

        # Aggregate by method
        from collections import Counter

        from app.db.models import PaymentMethod

        method_counts = Counter(opt.method for opt in payment_options)

        return {
            "yatra_id": yatra.id,
            "yatra_name": yatra.name,
            "total_options": len(payment_options),
            "summary": {
                "total": len(payment_options),
                "by_method": {
                    method.value: method_counts.get(method, 0)  # type: ignore[call-overload]
                    for method in PaymentMethod
                },
            },
            "payment_options": payment_options,
        }
