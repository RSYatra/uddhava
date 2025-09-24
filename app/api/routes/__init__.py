"""
API routes package initialization.

This package contains all API route modules organized by functionality.
"""

# Import all route modules for easy access
from . import devotees, health

__all__ = ["devotees", "health"]
