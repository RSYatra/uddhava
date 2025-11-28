"""
Helper utilities for yatra registration system.

This module contains utility functions for pricing calculation, group ID generation,
and member validation.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import RoomCategory, Yatra, YatraRegistration


def generate_group_id(yatra_id: int, yatra_start_date: date, db: Session) -> str:
    """
    Generate a unique group ID for yatra registrations.

    Format: GRP-{year}-{yatra_id}-{sequence}
    Example: GRP-2026-1-001

    Args:
        yatra_id: ID of the yatra
        yatra_start_date: Start date of the yatra (to get year)
        db: Database session

    Returns:
        Group ID string in format GRP-{year}-{yatra_id}-{sequence}
    """
    year = yatra_start_date.year

    # Get the maximum group_id for this yatra to determine next sequence
    max_group_id = (
        db.query(func.max(YatraRegistration.group_id))
        .filter(YatraRegistration.yatra_id == yatra_id)
        .scalar()
    )

    if max_group_id:
        # Extract sequence from "GRP-2026-1-001" format
        try:
            sequence = int(max_group_id.split("-")[-1]) + 1
        except (ValueError, IndexError):
            # Fallback if format is unexpected
            sequence = 1
    else:
        sequence = 1

    return f"GRP-{year}-{yatra_id}-{sequence:03d}"


def calculate_age_at_date(date_of_birth: date, reference_date: date) -> float:
    """
    Calculate age at a specific reference date.

    Args:
        date_of_birth: Date of birth
        reference_date: Date to calculate age at (e.g., yatra start date)

    Returns:
        Age in years (as float for precision)
    """
    age_in_days = (reference_date - date_of_birth).days
    age_in_years = age_in_days / 365.25
    return age_in_years


def calculate_member_price(
    member_dob: date,
    yatra_start_date: date,
    yatra_id: int,
    room_category_name: str,
    db: Session,
) -> Decimal:
    """
    Calculate price for a member based on age at yatra start date and room category.

    Children under 5 years old (at yatra start date) are free.
    Everyone else pays the full price for their room category.

    Args:
        member_dob: Member's date of birth
        yatra_start_date: Yatra start date (for age calculation)
        yatra_id: ID of the yatra
        room_category_name: Name of the room category
        db: Database session

    Returns:
        Price to charge for this member (Decimal)

    Raises:
        ValueError: If room category not found or inactive
    """
    # Calculate age at yatra start date
    age_at_yatra = calculate_age_at_date(member_dob, yatra_start_date)

    # Children under 5 are free
    if age_at_yatra < 5:
        return Decimal("0.00")

    # Get price for room category
    category = (
        db.query(RoomCategory)
        .filter(
            RoomCategory.yatra_id == yatra_id,
            RoomCategory.name == room_category_name,
            RoomCategory.is_active,
        )
        .first()
    )

    if not category:
        raise ValueError(
            f"Room category '{room_category_name}' not found or inactive for yatra {yatra_id}"
        )

    return Decimal(str(category.price_per_person))


def validate_yatra_capacity(yatra_id: int, db: Session) -> None:
    """
    Validate that yatra has capacity for new registrations.

    Note: Currently no capacity limit, but this function is kept for future use.

    Args:
        yatra_id: ID of the yatra
        db: Database session

    Raises:
        ValueError: If yatra is at capacity (not implemented yet)
    """
    # No capacity limit for now, as per requirements
    # This function is a placeholder for future implementation
    pass


def validate_room_category_exists_in_template(
    yatra_id: int, room_category_name: str, db: Session
) -> bool:
    """
    Check if a room category exists and is active for a yatra.

    Args:
        yatra_id: ID of the yatra
        room_category_name: Name of the room category
        db: Database session

    Returns:
        True if category exists and is active, False otherwise
    """
    category = (
        db.query(RoomCategory)
        .filter(
            RoomCategory.yatra_id == yatra_id,
            RoomCategory.name == room_category_name,
            RoomCategory.is_active,
        )
        .first()
    )

    return category is not None


def validate_payment_option_for_yatra(yatra_id: int, payment_option_id: int, db: Session) -> bool:
    """
    Check if a payment option is available for a yatra.

    Args:
        yatra_id: ID of the yatra
        payment_option_id: ID of the payment option
        db: Database session

    Returns:
        True if payment option is available for this yatra, False otherwise
    """
    from app.db.models import YatraPaymentOption

    link = (
        db.query(YatraPaymentOption)
        .filter(
            YatraPaymentOption.yatra_id == yatra_id,
            YatraPaymentOption.payment_option_id == payment_option_id,
        )
        .first()
    )

    return link is not None


def get_yatra_start_date(yatra_id: int, db: Session) -> date:
    """
    Get the start date of a yatra.

    Args:
        yatra_id: ID of the yatra
        db: Database session

    Returns:
        Yatra start date

    Raises:
        ValueError: If yatra not found
    """
    yatra = db.query(Yatra).filter(Yatra.id == yatra_id).first()

    if not yatra:
        raise ValueError(f"Yatra {yatra_id} not found")

    return yatra.start_date  # type: ignore[return-value]
