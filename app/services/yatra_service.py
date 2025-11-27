"""
Business logic service for yatra management.

This service handles yatra CRUD operations with validation and transaction management.
"""

import logging
import re
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.yatra_validators import validate_yatra_dates
from app.db.models import (
    PaymentOption,
    PricingTemplate,
    RegistrationStatus,
    Yatra,
    YatraPaymentOption,
    YatraStatus,
)
from app.repositories.yatra_repository import YatraRepository
from app.schemas.yatra import YatraCreate, YatraUpdate

logger = logging.getLogger(__name__)


class YatraService:
    """Service for yatra business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.repository = YatraRepository(db)

    @validate_yatra_dates
    def create_yatra(self, yatra_data: YatraCreate, admin_id: int) -> Yatra:
        """Create new yatra with validation."""
        try:
            # Validate pricing template exists
            pricing_template = (
                self.db.query(PricingTemplate)
                .filter(PricingTemplate.id == yatra_data.pricing_template_id)
                .first()
            )
            if not pricing_template:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Pricing template with ID {yatra_data.pricing_template_id} not found",
                )

            # Validate payment options exist
            payment_options = (
                self.db.query(PaymentOption)
                .filter(PaymentOption.id.in_(yatra_data.payment_option_ids))
                .all()
            )
            if len(payment_options) != len(yatra_data.payment_option_ids):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="One or more payment options not found",
                )

            slug = self._generate_slug(yatra_data.name)

            yatra_dict = yatra_data.model_dump(exclude={"payment_option_ids"})
            yatra_dict["slug"] = slug
            yatra_dict["created_by"] = admin_id

            yatra = self.repository.create(yatra_dict)
            self.db.flush()

            # Create yatra payment option associations
            for idx, payment_option_id in enumerate(yatra_data.payment_option_ids):
                yatra_payment = YatraPaymentOption(
                    yatra_id=yatra.id,
                    payment_option_id=payment_option_id,
                    display_order=idx,
                )
                self.db.add(yatra_payment)

            self.db.commit()

            logger.info(f"Yatra created: {yatra.id} by admin {admin_id}")
            return yatra

        except HTTPException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create yatra: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create yatra",
            )

    def get_yatra(self, yatra_id: int, include_stats: bool = True) -> dict:
        """Get yatra with optional statistics."""
        yatra = self.repository.get_by_id(yatra_id)
        if not yatra:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Yatra not found")

        result = {
            "yatra": yatra,
            "is_registration_open": self._is_registration_open(yatra),
        }

        if include_stats:
            result["stats"] = self._get_registration_stats(yatra_id)

        return result

    def list_yatras(
        self,
        status_filter: YatraStatus | None = None,
        upcoming_only: bool = False,
        featured_only: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """List yatras with pagination."""
        skip = (page - 1) * page_size

        yatras = self.repository.list_all(
            status=status_filter,
            upcoming_only=upcoming_only,
            featured_only=featured_only,
            skip=skip,
            limit=page_size,
        )

        return {
            "yatras": yatras,
            "page": page,
            "page_size": page_size,
            "has_more": len(yatras) == page_size,
        }

    def update_yatra(self, yatra_id: int, yatra_data: YatraUpdate, admin_id: int) -> Yatra:
        """Update yatra with validation."""
        try:
            yatra = self.repository.get_by_id(yatra_id)
            if not yatra:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Yatra not found")

            # Don't allow updating if yatra has already started (past date, not today)
            if yatra.start_date < date.today():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot update yatra that has already started",
                )

            # Validate pricing template if provided
            if yatra_data.pricing_template_id:
                pricing_template = (
                    self.db.query(PricingTemplate)
                    .filter(PricingTemplate.id == yatra_data.pricing_template_id)
                    .first()
                )
                if not pricing_template:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Pricing template with ID {yatra_data.pricing_template_id} not found",
                    )

            # Update payment options if provided
            if yatra_data.payment_option_ids is not None:
                # Validate payment options exist
                payment_options = (
                    self.db.query(PaymentOption)
                    .filter(PaymentOption.id.in_(yatra_data.payment_option_ids))
                    .all()
                )
                if len(payment_options) != len(yatra_data.payment_option_ids):
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="One or more payment options not found",
                    )

                # Delete existing payment option associations
                self.db.query(YatraPaymentOption).filter(
                    YatraPaymentOption.yatra_id == yatra_id
                ).delete()

                # Create new associations
                for idx, payment_option_id in enumerate(yatra_data.payment_option_ids):
                    yatra_payment = YatraPaymentOption(
                        yatra_id=yatra_id,
                        payment_option_id=payment_option_id,
                        display_order=idx,
                    )
                    self.db.add(yatra_payment)

            update_dict = yatra_data.model_dump(exclude_unset=True, exclude={"payment_option_ids"})
            yatra = self.repository.update(yatra, update_dict)
            self.db.commit()

            logger.info(f"Yatra {yatra_id} updated by admin {admin_id}")
            return yatra

        except HTTPException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update yatra: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update yatra",
            )

    def delete_yatra(self, yatra_id: int, admin_id: int) -> bool:
        """Soft delete yatra."""
        try:
            yatra = self.repository.get_by_id(yatra_id)
            if not yatra:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Yatra not found")

            # Check if there are confirmed registrations
            confirmed_count = self.repository.get_registration_count(
                yatra_id, status=RegistrationStatus.CONFIRMED.value
            )

            if confirmed_count > 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot delete yatra with {confirmed_count} confirmed registrations",
                )

            self.repository.soft_delete(yatra)
            self.db.commit()

            logger.info(f"Yatra {yatra_id} deleted by admin {admin_id}")
            return True

        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete yatra: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete yatra",
            )

    def _get_registration_stats(self, yatra_id: int) -> dict:
        """Get registration statistics for a yatra."""
        return {
            "total": self.repository.get_registration_count(yatra_id),
            "pending": self.repository.get_registration_count(
                yatra_id, RegistrationStatus.PENDING.value
            ),
            "payment_submitted": self.repository.get_registration_count(
                yatra_id, RegistrationStatus.PAYMENT_SUBMITTED.value
            ),
            "confirmed": self.repository.get_registration_count(
                yatra_id, RegistrationStatus.CONFIRMED.value
            ),
            "completed": self.repository.get_registration_count(
                yatra_id, RegistrationStatus.COMPLETED.value
            ),
        }

    def _is_registration_open(self, yatra: Yatra) -> bool:
        """Check if registration is currently open."""
        today = date.today()
        return (
            yatra.status == YatraStatus.UPCOMING
            and yatra.registration_start_date <= today <= yatra.registration_deadline
        )

    def _generate_slug(self, name: str) -> str:
        """Generate URL-friendly slug from yatra name."""
        slug = name.lower()
        slug = re.sub(r"[^a-z0-9]+", "-", slug)
        slug = slug.strip("-")

        # Ensure uniqueness
        base_slug = slug
        counter = 1
        while self.repository.get_by_slug(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1

        return slug

    def get_yatra_pricing_template(self, yatra_id: int) -> PricingTemplate | None:
        """Get pricing template for a yatra."""
        yatra = self.repository.get_by_id(yatra_id)
        if not yatra:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Yatra not found")

        return (
            self.db.query(PricingTemplate)
            .filter(PricingTemplate.id == yatra.pricing_template_id)
            .first()
        )

    def get_yatra_payment_options(self, yatra_id: int) -> list[PaymentOption]:
        """Get payment options for a yatra."""
        yatra = self.repository.get_by_id(yatra_id)
        if not yatra:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Yatra not found")

        return (
            self.db.query(PaymentOption)
            .join(YatraPaymentOption)
            .filter(YatraPaymentOption.yatra_id == yatra_id)
            .order_by(YatraPaymentOption.display_order)
            .all()
        )
