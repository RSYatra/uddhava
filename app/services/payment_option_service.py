"""
Service for payment option management.

This module handles CRUD operations for payment options.
"""

import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import PaymentOption
from app.schemas.payment_option import PaymentOptionCreate, PaymentOptionUpdate

logger = logging.getLogger(__name__)


class PaymentOptionService:
    """Service for managing payment options."""

    def __init__(self, db: Session):
        self.db = db

    def create_payment_option(self, payment_data: PaymentOptionCreate) -> PaymentOption:
        """
        Create a new payment option.

        Args:
            payment_data: Payment option creation data

        Returns:
            Created payment option

        Raises:
            HTTPException: If payment option name already exists
        """
        # Check if name already exists
        existing = (
            self.db.query(PaymentOption).filter(PaymentOption.name == payment_data.name).first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payment option with name '{payment_data.name}' already exists",
            )

        # Create payment option
        payment_option = PaymentOption(
            name=payment_data.name,
            payment_method=payment_data.payment_method,
            bank_account_number=payment_data.bank_account_number,
            ifsc_code=payment_data.ifsc_code,
            bank_name=payment_data.bank_name,
            branch_name=payment_data.branch_name,
            account_holder_name=payment_data.account_holder_name,
            account_type=payment_data.account_type,
            upi_id=payment_data.upi_id,
            upi_phone_number=payment_data.upi_phone_number,
            qr_code_path=payment_data.qr_code_path,
            notes=payment_data.notes,
            is_active=True,
        )
        self.db.add(payment_option)
        self.db.commit()
        self.db.refresh(payment_option)
        logger.info(f"Created payment option: {payment_option.name} (ID: {payment_option.id})")
        return payment_option

    def get_payment_option(self, payment_option_id: int) -> PaymentOption:
        """
        Get a payment option by ID.

        Args:
            payment_option_id: Payment option ID

        Returns:
            Payment option

        Raises:
            HTTPException: If payment option not found
        """
        payment_option = (
            self.db.query(PaymentOption).filter(PaymentOption.id == payment_option_id).first()
        )
        if not payment_option:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Payment option with ID {payment_option_id} not found",
            )
        return payment_option

    def list_payment_options(self, active_only: bool = True) -> list[PaymentOption]:
        """
        List all payment options.

        Args:
            active_only: If True, return only active payment options

        Returns:
            List of payment options
        """
        query = self.db.query(PaymentOption)
        if active_only:
            query = query.filter(PaymentOption.is_active == True)  # noqa: E712
        return query.all()

    def update_payment_option(
        self, payment_option_id: int, payment_data: PaymentOptionUpdate
    ) -> PaymentOption:
        """
        Update a payment option.

        Args:
            payment_option_id: Payment option ID
            payment_data: Updated payment option data

        Returns:
            Updated payment option

        Raises:
            HTTPException: If payment option not found or name conflict
        """
        payment_option = self.get_payment_option(payment_option_id)

        # Check name uniqueness if name is being updated
        if payment_data.name and payment_data.name != payment_option.name:
            existing = (
                self.db.query(PaymentOption)
                .filter(
                    PaymentOption.name == payment_data.name,
                    PaymentOption.id != payment_option_id,
                )
                .first()
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Payment option with name '{payment_data.name}' already exists",
                )

        # Update fields
        if payment_data.name:
            payment_option.name = payment_data.name
        if payment_data.is_active is not None:
            payment_option.is_active = payment_data.is_active
        if payment_data.bank_account_number is not None:
            payment_option.bank_account_number = payment_data.bank_account_number
        if payment_data.ifsc_code is not None:
            payment_option.ifsc_code = payment_data.ifsc_code
        if payment_data.bank_name is not None:
            payment_option.bank_name = payment_data.bank_name
        if payment_data.branch_name is not None:
            payment_option.branch_name = payment_data.branch_name
        if payment_data.account_holder_name is not None:
            payment_option.account_holder_name = payment_data.account_holder_name
        if payment_data.account_type is not None:
            payment_option.account_type = payment_data.account_type
        if payment_data.upi_id is not None:
            payment_option.upi_id = payment_data.upi_id
        if payment_data.upi_phone_number is not None:
            payment_option.upi_phone_number = payment_data.upi_phone_number
        if payment_data.qr_code_path is not None:
            payment_option.qr_code_path = payment_data.qr_code_path
        if payment_data.notes is not None:
            payment_option.notes = payment_data.notes

        self.db.commit()
        self.db.refresh(payment_option)
        logger.info(f"Updated payment option: {payment_option.name} (ID: {payment_option.id})")
        return payment_option

    def delete_payment_option(self, payment_option_id: int) -> None:
        """
        Delete a payment option.

        Args:
            payment_option_id: Payment option ID

        Raises:
            HTTPException: If payment option not found or in use by yatras
        """
        payment_option = self.get_payment_option(payment_option_id)

        # Check if payment option is in use
        from app.db.models import YatraPaymentOption

        usage_count = (
            self.db.query(YatraPaymentOption)
            .filter(YatraPaymentOption.payment_option_id == payment_option_id)
            .count()
        )
        if usage_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete payment option. It is used by {usage_count} yatra(s)",
            )

        # Delete payment option
        self.db.delete(payment_option)
        self.db.commit()
        logger.info(f"Deleted payment option: {payment_option.name} (ID: {payment_option.id})")
