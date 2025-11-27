"""
API routes package initialization.

This package contains all API route modules organized by functionality.
"""

# Import all route modules for easy access
from . import (
    centers,
    country_codes,
    devotee_auth,
    devotees,
    health,
    payment_options,
    pricing_templates,
    spiritual_masters,
    yatra_registrations,
    yatra_registrations_v2,
    yatras,
)

__all__ = [
    "centers",
    "country_codes",
    "devotee_auth",
    "devotees",
    "health",
    "payment_options",
    "pricing_templates",
    "spiritual_masters",
    "yatra_registrations",
    "yatra_registrations_v2",
    "yatras",
]
