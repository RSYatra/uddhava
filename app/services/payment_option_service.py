"""
Business logic service for payment option management.

This service handles CRUD operations for reusable payment options
that can be associated with multiple yatras.
"""

import logging

from fastapi import status
from sqlalchemy.orm import Session

from app.core.responses import StandardHTTPException
from app.db.models import PaymentOption, YatraPaymentOption
from app.schemas.payment_option import PaymentOptionCreate, PaymentOptionUpdate

logger = logging.getLogger(__name__)


class PaymentOptionService:
    """Service for payment option business logic."""

    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db

    def create_payment_option(self, option_data: PaymentOptionCreate) -> PaymentOption:
        """
        Create a new payment option.

        Args:
            option_data: Payment option creation data

        Returns:
            Created PaymentOption object

        Raises:
            HTTPException: For validation errors or system failures
        """
        try:
            payment_option = PaymentOption(
                name=option_data.name,
                method=option_data.method,
                upi_id=option_data.upi_id,
                account_number=option_data.account_number,
                bank_name=option_data.bank_name,
                ifsc_code=option_data.ifsc_code,
                account_holder=option_data.account_holder,
                branch=option_data.branch,
                qr_code_url=option_data.qr_code_url,
                instructions=option_data.instructions,
                is_active=True,  # Default to active
            )
            self.db.add(payment_option)
            self.db.commit()
            self.db.refresh(payment_option)

            logger.info(f"Created payment option: {payment_option.id} - {payment_option.name}")
            return payment_option

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create payment option: {e}")
            raise StandardHTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Failed to create payment option: {str(e)}",
            )

    def get_payment_option(self, option_id: int) -> PaymentOption:
        """
        Get payment option by ID.

        Args:
            option_id: Payment option ID

        Returns:
            PaymentOption object

        Raises:
            HTTPException: If payment option not found
        """
        payment_option = self.db.query(PaymentOption).filter(PaymentOption.id == option_id).first()

        if not payment_option:
            raise StandardHTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Payment option not found",
                success=False,
                data=None,
            )

        return payment_option

    def list_payment_options(self, active_only: bool = False) -> list[PaymentOption]:
        """
        List all payment options.

        Args:
            active_only: If True, only return active payment options

        Returns:
            List of PaymentOption objects
        """
        query = self.db.query(PaymentOption)

        if active_only:
            query = query.filter(PaymentOption.is_active)

        return query.order_by(PaymentOption.name).all()

    def update_payment_option(
        self, option_id: int, update_data: PaymentOptionUpdate
    ) -> PaymentOption:
        """
        Update payment option.

        Args:
            option_id: Payment option ID
            update_data: Update data

        Returns:
            Updated PaymentOption object

        Raises:
            HTTPException: If payment option not found or update fails
        """
        payment_option = self.get_payment_option(option_id)

        try:
            update_dict = update_data.model_dump(exclude_unset=True)
            for key, value in update_dict.items():
                if key == "payment_method":
                    payment_option.method = value
                else:
                    setattr(payment_option, key, value)

            self.db.commit()
            self.db.refresh(payment_option)

            logger.info(f"Updated payment option: {payment_option.id}")
            return payment_option

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update payment option: {e}")
            raise StandardHTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Failed to update payment option: {str(e)}",
            )

    def delete_payment_option(self, option_id: int) -> None:
        """
        Delete payment option.

        Args:
            option_id: Payment option ID

        Raises:
            HTTPException: If payment option not found or deletion fails
        """
        payment_option = self.get_payment_option(option_id)

        try:
            self.db.delete(payment_option)
            self.db.commit()

            logger.info(f"Deleted payment option: {option_id}")

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete payment option: {e}")
            raise StandardHTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Failed to delete payment option: {str(e)}",
            )

    def add_payment_option_to_yatra(self, yatra_id: int, option_id: int) -> None:
        """
        Associate a payment option with a yatra.

        Args:
            yatra_id: Yatra ID
            option_id: Payment option ID

        Raises:
            HTTPException: If association already exists or creation fails
        """
        # Check if association already exists
        existing = (
            self.db.query(YatraPaymentOption)
            .filter(
                YatraPaymentOption.yatra_id == yatra_id,
                YatraPaymentOption.payment_option_id == option_id,
            )
            .first()
        )

        if existing:
            raise StandardHTTPException(
                status_code=status.HTTP_409_CONFLICT,
                message="Payment option already associated with this yatra",
                success=False,
                data=None,
            )

        try:
            yatra_payment_option = YatraPaymentOption(
                yatra_id=yatra_id,
                payment_option_id=option_id,
            )
            self.db.add(yatra_payment_option)
            self.db.commit()

            logger.info(f"Added payment option {option_id} to yatra {yatra_id}")

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to add payment option to yatra: {e}")
            raise StandardHTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Failed to add payment option to yatra: {str(e)}",
            )

    def remove_payment_option_from_yatra(self, yatra_id: int, option_id: int) -> None:
        """
        Remove payment option association from a yatra.

        Args:
            yatra_id: Yatra ID
            option_id: Payment option ID

        Raises:
            HTTPException: If association not found or removal fails
        """
        yatra_payment_option = (
            self.db.query(YatraPaymentOption)
            .filter(
                YatraPaymentOption.yatra_id == yatra_id,
                YatraPaymentOption.payment_option_id == option_id,
            )
            .first()
        )

        if not yatra_payment_option:
            raise StandardHTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Payment option not associated with this yatra",
                success=False,
                data=None,
            )

        try:
            self.db.delete(yatra_payment_option)
            self.db.commit()

            logger.info(f"Removed payment option {option_id} from yatra {yatra_id}")

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to remove payment option from yatra: {e}")
            raise StandardHTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Failed to remove payment option from yatra: {str(e)}",
            )
