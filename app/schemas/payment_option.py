"""
Pydantic schemas for payment options.

This module defines the request and response schemas for payment option management.
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class PaymentOptionCreate(BaseModel):
    """Schema for creating a payment option."""

    name: str = Field(..., min_length=1, max_length=127)
    payment_method: str = Field(..., pattern="^(BANK|UPI)$")

    # Bank Details (required if payment_method is BANK)
    bank_account_number: str | None = Field(None, max_length=50)
    ifsc_code: str | None = Field(None, max_length=20)
    bank_name: str | None = Field(None, max_length=100)
    branch_name: str | None = Field(None, max_length=100)
    account_holder_name: str | None = Field(None, max_length=127)
    account_type: str | None = Field(None, max_length=50)

    # UPI Details (required if payment_method is UPI)
    upi_id: str | None = Field(None, max_length=100)
    upi_phone_number: str | None = Field(None, max_length=20)
    qr_code_path: str | None = Field(None, max_length=512)

    notes: str | None = None

    @field_validator("bank_account_number", "ifsc_code", "bank_name")
    @classmethod
    def validate_bank_details(cls, v: str | None, info) -> str | None:
        """Validate that bank details are provided if payment method is BANK."""
        if info.data.get("payment_method") == "BANK" and not v:
            raise ValueError(f"{info.field_name} is required for BANK payment method")
        return v

    @field_validator("upi_id")
    @classmethod
    def validate_upi_details(cls, v: str | None, info) -> str | None:
        """Validate that UPI details are provided if payment method is UPI."""
        if info.data.get("payment_method") == "UPI" and not v:
            raise ValueError("upi_id is required for UPI payment method")
        return v


class PaymentOptionUpdate(BaseModel):
    """Schema for updating a payment option."""

    name: str | None = Field(None, min_length=1, max_length=127)
    is_active: bool | None = None

    # Bank Details
    bank_account_number: str | None = Field(None, max_length=50)
    ifsc_code: str | None = Field(None, max_length=20)
    bank_name: str | None = Field(None, max_length=100)
    branch_name: str | None = Field(None, max_length=100)
    account_holder_name: str | None = Field(None, max_length=127)
    account_type: str | None = Field(None, max_length=50)

    # UPI Details
    upi_id: str | None = Field(None, max_length=100)
    upi_phone_number: str | None = Field(None, max_length=20)
    qr_code_path: str | None = Field(None, max_length=512)

    notes: str | None = None


class PaymentOptionOut(BaseModel):
    """Schema for payment option output."""

    id: int
    name: str
    payment_method: str

    # Bank Details
    bank_account_number: str | None
    ifsc_code: str | None
    bank_name: str | None
    branch_name: str | None
    account_holder_name: str | None
    account_type: str | None

    # UPI Details
    upi_id: str | None
    upi_phone_number: str | None
    qr_code_path: str | None

    is_active: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True


class PaymentOptionListResponse(BaseModel):
    """Schema for payment option list response."""

    success: bool = True
    status_code: int = 200
    message: str = "Payment options retrieved successfully"
    data: list[PaymentOptionOut]
