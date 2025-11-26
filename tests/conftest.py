"""
Pytest configuration and shared fixtures.

This file is automatically loaded by pytest before any tests run.
"""

import os

# Set test environment variables BEFORE any app imports
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["ENVIRONMENT"] = "testing"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing"
os.environ["USE_GCS"] = "false"  # Disable GCS for tests
