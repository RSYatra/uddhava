"""
Pydantic schemas for payment options.

This module defines the request and response schemas for payment option management.
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.db.models import PaymentMethod


class PaymentOptionBase(BaseModel):
    """Base schema for payment option."""

    name: str = Field(..., min_length=1, max_length=255, description="Payment option name")
    method: PaymentMethod = Field(..., description="Payment method type")
    instructions: str | None = Field(None, description="Payment instructions for users")


class PaymentOptionCreate(PaymentOptionBase):
    """
    Schema for creating a payment option.

    **REQUIRED FIELDS:**
    - name (string, 1-255 chars): Payment option name (e.g., "ISKCON Vrindavan UPI")
    - method (enum): Payment method - UPI, BANK_TRANSFER, QR_CODE, CASH, or CHEQUE

    **CONDITIONAL FIELDS (based on method):**
    - For UPI: upi_id (required)
    - For BANK_TRANSFER: account_holder, account_number, ifsc_code, bank_name (all required)
    - For QR_CODE: qr_code_url (required)

    **OPTIONAL FIELDS:**
    - instructions (string): Payment instructions
    - branch (string): Bank branch name (for BANK_TRANSFER)
    - qr_code_url (string): QR code image URL (can be used with UPI too)
    """

    # UPI Details
    upi_id: str | None = Field(None, max_length=100, description="UPI ID (required for UPI method)")

    # Bank Details
    account_holder: str | None = Field(None, max_length=255, description="Account holder name")
    account_number: str | None = Field(None, max_length=50, description="Bank account number")
    ifsc_code: str | None = Field(None, max_length=20, description="IFSC code")
    bank_name: str | None = Field(None, max_length=255, description="Bank name")
    branch: str | None = Field(None, max_length=255, description="Bank branch")

    # QR Code
    qr_code_url: str | None = Field(None, max_length=500, description="QR code image URL")

    @field_validator("upi_id")
    @classmethod
    def validate_upi_details(cls, v: str | None, info) -> str | None:
        """Validate that UPI ID is provided if payment method is UPI."""
        if info.data.get("method") == PaymentMethod.UPI and not v:
            raise ValueError("upi_id is required for UPI payment method")
        return v

    @field_validator("account_number", "ifsc_code", "bank_name", "account_holder")
    @classmethod
    def validate_bank_details(cls, v: str | None, info) -> str | None:
        """Validate that bank details are provided if payment method is BANK_TRANSFER."""
        if info.data.get("method") == PaymentMethod.BANK_TRANSFER and not v:
            raise ValueError(f"{info.field_name} is required for BANK_TRANSFER payment method")
        return v

    @field_validator("qr_code_url")
    @classmethod
    def validate_qr_code(cls, v: str | None, info) -> str | None:
        """Validate that QR code URL is provided if payment method is QR_CODE."""
        if info.data.get("method") == PaymentMethod.QR_CODE and not v:
            raise ValueError("qr_code_url is required for QR_CODE payment method")
        return v


class PaymentOptionUpdate(BaseModel):
    """Schema for updating a payment option."""

    name: str | None = Field(None, min_length=1, max_length=255)
    instructions: str | None = None
    is_active: bool | None = None

    # UPI Details
    upi_id: str | None = Field(None, max_length=100)

    # Bank Details
    account_holder: str | None = Field(None, max_length=255)
    account_number: str | None = Field(None, max_length=50)
    ifsc_code: str | None = Field(None, max_length=20)
    bank_name: str | None = Field(None, max_length=255)
    branch: str | None = Field(None, max_length=255)

    # QR Code
    qr_code_url: str | None = Field(None, max_length=500)


class PaymentOptionOut(PaymentOptionBase):
    """Schema for payment option output."""

    id: int = Field(..., description="Unique payment option ID")
    method: PaymentMethod = Field(..., description="Payment method type")

    # UPI Details
    upi_id: str | None = Field(None, description="UPI ID")

    # Bank Details
    account_holder: str | None = Field(None, description="Account holder name")
    account_number: str | None = Field(None, description="Bank account number")
    ifsc_code: str | None = Field(None, description="IFSC code")
    bank_name: str | None = Field(None, description="Bank name")
    branch: str | None = Field(None, description="Bank branch")

    # QR Code
    qr_code_url: str | None = Field(None, description="QR code image URL")

    is_active: bool = Field(..., description="Whether the payment option is active")
    created_at: datetime = Field(..., description="When the payment option was created")
    updated_at: datetime = Field(..., description="When the payment option was last updated")

    class Config:
        from_attributes = True


class PaymentOptionListResponse(BaseModel):
    """Schema for payment option list response."""

    success: bool = True
    status_code: int = 200
    message: str = "Payment options retrieved successfully"
    data: list[PaymentOptionOut]
