"""
Reference data module.

This module contains curated reference data for the application,
loaded from CSV files and stored as Python constants for fast access.
"""

from app.data.centers import CENTERS
from app.data.country_codes import COUNTRY_CODES
from app.data.spiritual_masters import SPIRITUAL_MASTERS

__all__ = ["CENTERS", "COUNTRY_CODES", "SPIRITUAL_MASTERS"]
