"""
Password validation utilities.

Shared password strength validation functions for consistent
password requirements across signup, login, and reset.
"""


def validate_password_strength(password: str) -> str:
    """
    Validate password strength requirements.

    Requirements:
    - At least 8 characters long
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character

    Args:
        password: Password to validate

    Returns:
        The password if valid

    Raises:
        ValueError: If password doesn't meet requirements
    """
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")

    # Check for at least one uppercase letter
    if not any(c.isupper() for c in password):
        raise ValueError("Password must contain at least one uppercase letter")

    # Check for at least one lowercase letter
    if not any(c.islower() for c in password):
        raise ValueError("Password must contain at least one lowercase letter")

    # Check for at least one digit
    if not any(c.isdigit() for c in password):
        raise ValueError("Password must contain at least one number")

    # Check for at least one special character
    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not any(c in special_chars for c in password):
        raise ValueError("Password must contain at least one special character")

    return password
