"""
API routes package initialization.

This package contains all API route modules organized by functionality.
"""

# Import all route modules for easy access
from . import auth, devotees, health, users

__all__ = ["auth", "devotees", "health", "users"]
