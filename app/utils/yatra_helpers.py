"""
Helper utilities for yatra registration system.

This module contains utility functions for pricing calculation, group ID generation,
and member validation.
"""

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from app.db.models import PricingTemplateDetail
from app.schemas.yatra_member import YatraMemberCreate

if TYPE_CHECKING:
    pass


def generate_group_id() -> str:
    """
    Generate a unique group ID for yatra registrations.

    Returns:
        UUID string for group identification
    """
    return str(uuid.uuid4())


def calculate_age(date_of_birth: date) -> int:
    """
    Calculate age from date of birth.

    Args:
        date_of_birth: Date of birth

    Returns:
        Age in years
    """
    today = date.today()
    age = today.year - date_of_birth.year
    if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
        age -= 1
    return age


def calculate_member_price(
    member: YatraMemberCreate,
    pricing_details: list[PricingTemplateDetail],
) -> tuple[int, bool]:
    """
    Calculate price for a member based on age and room category.

    Args:
        member: Member data
        pricing_details: Pricing template details for all room categories

    Returns:
        Tuple of (price_charged, is_free)
    """
    # Check if member is under 5 years old (free)
    if member.date_of_birth:
        age = calculate_age(member.date_of_birth)
        if age < 5:
            return (0, True)

    # Find pricing for the member's room category
    for detail in pricing_details:
        if detail.room_category == member.room_category:
            # price_per_person is an Integer column, so it's already an int when queried
            price: int = detail.price_per_person  # type: ignore[assignment]
            return (price, False)

    # Fallback (should not happen if validation is correct)
    return (0, False)


def validate_member_dates(
    member: YatraMemberCreate,
    yatra_start_date: date,
    yatra_end_date: date,
) -> None:
    """
    Validate that member's arrival and departure dates are within yatra period.

    Args:
        member: Member data
        yatra_start_date: Yatra start date
        yatra_end_date: Yatra end date

    Raises:
        ValueError: If dates are invalid
    """
    arrival_date = member.arrival_datetime.date()
    departure_date = member.departure_datetime.date()

    if arrival_date < yatra_start_date:
        raise ValueError(
            f"Arrival date {arrival_date} cannot be before yatra start date {yatra_start_date}"
        )

    if departure_date > yatra_end_date:
        raise ValueError(
            f"Departure date {departure_date} cannot be after yatra end date {yatra_end_date}"
        )

    if member.departure_datetime <= member.arrival_datetime:
        raise ValueError("Departure date and time must be after arrival date and time")


def generate_registration_number(yatra_id: int, sequence: int) -> str:
    """
    Generate a unique registration number.

    Format: YTR-{YEAR}-{YATRA_ID}-{SEQUENCE}

    Args:
        yatra_id: Yatra ID
        sequence: Sequential number for the registration

    Returns:
        Registration number string
    """
    year = datetime.now().year
    return f"YTR-{year}-{yatra_id:03d}-{sequence:04d}"
