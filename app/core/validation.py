"""
API validation utilities and custom validators.

This module provides enhanced validation for API requests,
including custom validators, input sanitization, and security checks.
"""

import re
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from fastapi import HTTPException, status
from pydantic import BaseModel, field_validator, model_validator
from pydantic_core import ValidationError


class ValidationUtils:
    """Utility class for common validation operations."""

    # Common regex patterns
    PHONE_PATTERN = re.compile(r"^\+?1?\d{9,15}$")
    USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_]{3,20}$")
    SAFE_STRING_PATTERN = re.compile(r"^[a-zA-Z0-9\s\-_.@]+$")

    @staticmethod
    def validate_phone_number(phone: str) -> str:
        """Validate and normalize phone number."""
        # Remove spaces and special characters
        cleaned = re.sub(r"[^\d+]", "", phone)
        if not ValidationUtils.PHONE_PATTERN.match(cleaned):
            raise ValueError("Invalid phone number format")
        return cleaned

    @staticmethod
    def validate_username(username: str) -> str:
        """Validate username format."""
        if not ValidationUtils.USERNAME_PATTERN.match(username):
            raise ValueError(
                "Username must be 3-20 characters, alphanumeric and underscore only"
            )
        return username.lower()

    @staticmethod
    def sanitize_string(value: str, max_length: int = 255) -> str:
        """Sanitize string input to prevent injection attacks."""
        # Remove potential script tags and suspicious content
        cleaned = re.sub(r"<[^>]*>", "", value)  # Remove HTML tags
        cleaned = re.sub(r"[^\w\s\-_.@]", "", cleaned)  # Keep only safe chars
        cleaned = cleaned.strip()[:max_length]  # Limit length
        return cleaned

    @staticmethod
    def validate_url(url: str) -> str:
        """Validate URL format and security."""
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("Invalid URL format")
            if parsed.scheme not in ["http", "https"]:
                raise ValueError("URL must use HTTP or HTTPS")
            return url
        except Exception:
            raise ValueError("Invalid URL")


class EnhancedValidationMixin(BaseModel):
    """
    Mixin class providing enhanced validation features.

    Includes:
    - Input sanitization
    - Rate limiting validation
    - Security checks
    """

    @model_validator(mode="before")
    def sanitize_inputs(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize string inputs to prevent injection attacks."""
        if isinstance(values, dict):
            sanitized = {}
            for key, value in values.items():
                if isinstance(value, str) and key not in [
                    "password",
                    "password_hash",
                ]:
                    sanitized[key] = ValidationUtils.sanitize_string(value)
                else:
                    sanitized[key] = value
            return sanitized
        return values


class PaginationParams(BaseModel):
    """Standardized pagination parameters."""

    page: int = 1
    limit: int = 20

    @field_validator("page")
    def validate_page(cls, v):
        if v < 1:
            raise ValueError("Page must be greater than 0")
        if v > 1000:  # Reasonable upper limit
            raise ValueError("Page number too large")
        return v

    @field_validator("limit")
    def validate_limit(cls, v):
        if v < 1:
            raise ValueError("Limit must be greater than 0")
        if v > 100:  # Prevent large queries
            raise ValueError("Limit cannot exceed 100")
        return v

    @property
    def offset(self) -> int:
        """Calculate offset for database queries."""
        return (self.page - 1) * self.limit


class SortParams(BaseModel):
    """Standardized sorting parameters."""

    sort_by: Optional[str] = None
    sort_order: str = "asc"

    @field_validator("sort_order")
    def validate_sort_order(cls, v):
        if v.lower() not in ["asc", "desc"]:
            raise ValueError("Sort order must be 'asc' or 'desc'")
        return v.lower()


class FileUploadValidation:
    """Validation utilities for file uploads."""

    ALLOWED_IMAGE_TYPES = {
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
    }

    ALLOWED_DOCUMENT_TYPES = {
        "application/pdf",
        "text/plain",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }

    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

    @staticmethod
    def validate_image(content_type: str, size: int) -> None:
        """Validate image upload."""
        if content_type not in FileUploadValidation.ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Invalid image type. Allowed: "
                    f"{', '.join(FileUploadValidation.ALLOWED_IMAGE_TYPES)}"
                ),
            )

        if size > FileUploadValidation.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"File too large. Maximum size: "
                    f"{FileUploadValidation.MAX_FILE_SIZE // (1024*1024)}MB"
                ),
            )

    @staticmethod
    def validate_document(content_type: str, size: int) -> None:
        """Validate document upload."""
        if content_type not in FileUploadValidation.ALLOWED_DOCUMENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Invalid document type. Allowed: "
                    f"{', '.join(FileUploadValidation.ALLOWED_DOCUMENT_TYPES)}"
                ),
            )

        if size > FileUploadValidation.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"File too large. Maximum size: "
                    f"{FileUploadValidation.MAX_FILE_SIZE // (1024*1024)}MB"
                ),
            )


def validate_json_request(
    data: Dict[str, Any], max_size: int = 1024 * 1024
) -> Dict[str, Any]:
    """
    Validate JSON request size and structure.

    Args:
        data: Request data
        max_size: Maximum allowed size in bytes

    Returns:
        Validated data

    Raises:
        HTTPException: If validation fails
    """
    import json

    # Check size
    json_str = json.dumps(data)
    if len(json_str.encode("utf-8")) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Request payload too large",
        )

    # Check depth (prevent deeply nested objects)
    def check_depth(obj, depth=0, max_depth=10):
        if depth > max_depth:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Request payload too deeply nested",
            )

        if isinstance(obj, dict):
            for value in obj.values():
                check_depth(value, depth + 1, max_depth)
        elif isinstance(obj, list):
            for item in obj:
                check_depth(item, depth + 1, max_depth)

    check_depth(data)
    return data


class APIErrorHandler:
    """Centralized error handling for API validation."""

    @staticmethod
    def handle_validation_error(error: ValidationError) -> HTTPException:
        """Convert Pydantic validation error to HTTP exception."""
        errors = []
        for err in error.errors():
            field = " -> ".join(str(loc) for loc in err["loc"])
            errors.append({"field": field, "message": err["msg"], "type": err["type"]})

        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Validation failed", "errors": errors},
        )

    @staticmethod
    def handle_database_error(error: Exception) -> HTTPException:
        """Handle database-related errors."""
        import logging

        logger = logging.getLogger("app.api")
        logger.error(f"Database error: {error}")

        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
