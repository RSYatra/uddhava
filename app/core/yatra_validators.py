"""
Validation decorators for yatra operations.

This module provides reusable validation decorators for yatra and registration
business logic with clean error handling.
"""

from collections.abc import Callable
from functools import wraps
from typing import Any

from fastapi import HTTPException, status


class YatraValidationError(HTTPException):
    """Custom exception for yatra validation errors."""

    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def validate_yatra_dates(func: Callable) -> Callable:
    """
    Validate yatra date logic.

    Ensures:
    - registration_start_date < registration_deadline < start_date < end_date
    - Future dates for new yatras
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        yatra_data = kwargs.get("yatra_data") or (args[1] if len(args) > 1 else None)

        if not yatra_data:
            return func(*args, **kwargs)

        # Validate date sequence
        if yatra_data.registration_start_date >= yatra_data.registration_deadline:
            raise YatraValidationError("Registration start must be before deadline")

        if yatra_data.registration_deadline >= yatra_data.start_date:
            raise YatraValidationError("Registration deadline must be before yatra start")

        if yatra_data.start_date >= yatra_data.end_date:
            raise YatraValidationError("Start date must be before end date")

        return func(*args, **kwargs)

    return wrapper


def validate_registration_dates(func: Callable) -> Callable:
    """
    Validate registration travel dates.

    Ensures arrival_datetime < departure_datetime
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        reg_data = kwargs.get("reg_data") or (args[2] if len(args) > 2 else None)

        if not reg_data:
            return func(*args, **kwargs)

        if reg_data.arrival_datetime >= reg_data.departure_datetime:
            raise YatraValidationError("Arrival must be before departure")

        return func(*args, **kwargs)

    return wrapper


def validate_registration_capacity(func: Callable) -> Callable:
    """
    Validate number of members and accompanying members count.

    Ensures:
    - 1 <= number_of_members <= 20
    - accompanying_members count matches number_of_members - 1
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        reg_data = kwargs.get("reg_data") or (args[2] if len(args) > 2 else None)

        if not reg_data:
            return func(*args, **kwargs)

        if reg_data.number_of_members < 1:
            raise YatraValidationError("At least one member required")

        if reg_data.number_of_members > 20:
            raise YatraValidationError("Maximum 20 members per registration")

        # Validate accompanying members count
        expected_accompanying = reg_data.number_of_members - 1
        actual_accompanying = (
            len(reg_data.accompanying_members) if reg_data.accompanying_members else 0
        )

        if actual_accompanying != expected_accompanying:
            raise YatraValidationError(
                f"Number of accompanying members ({actual_accompanying}) must match "
                f"total members - 1 ({expected_accompanying})"
            )

        return func(*args, **kwargs)

    return wrapper


def validate_status_transition(allowed_transitions: dict) -> Callable:
    """
    Decorator factory for status transition validation.

    Args:
        allowed_transitions: Dict mapping current status to list of allowed next statuses

    Usage:
        @validate_status_transition({
            RegistrationStatus.PENDING: [RegistrationStatus.PAYMENT_SUBMITTED],
            ...
        })
        def update_status(self, ...):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            current_status = kwargs.get("current_status")
            new_status = kwargs.get("new_status")

            if not current_status or not new_status:
                return func(*args, **kwargs)

            if current_status not in allowed_transitions:
                raise YatraValidationError(f"Invalid current status: {current_status}")

            if new_status not in allowed_transitions[current_status]:
                raise YatraValidationError(
                    f"Cannot transition from {current_status.value} to {new_status.value}. "
                    f"Allowed: {[s.value for s in allowed_transitions[current_status]]}"
                )

            return func(*args, **kwargs)

        return wrapper

    return decorator
