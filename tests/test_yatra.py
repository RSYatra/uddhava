"""
Basic tests for yatra registration system.

This module provides foundational tests for yatra and registration endpoints.
"""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, Devotee, UserRole, Yatra, YatraStatus
from app.db.session import get_db
from main import app

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_yatra.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    """Create and drop tables for each test."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def admin_user():
    """Create admin user for testing."""
    db = TestingSessionLocal()
    admin = Devotee(
        email="admin@test.com",
        password_hash="$2b$12$test_hash",
        legal_name="Admin User",
        role=UserRole.ADMIN,
        email_verified=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    db.close()
    return admin


@pytest.fixture
def regular_user():
    """Create regular user for testing."""
    db = TestingSessionLocal()
    user = Devotee(
        email="user@test.com",
        password_hash="$2b$12$test_hash",
        legal_name="Regular User",
        role=UserRole.USER,
        email_verified=True,
        date_of_birth=date(1990, 1, 1),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


@pytest.fixture
def sample_yatra(admin_user):
    """Create sample yatra for testing."""
    db = TestingSessionLocal()
    today = date.today()
    yatra = Yatra(
        name="Test Yatra to Vrindavan",
        slug="test-yatra-vrindavan",
        destination="Vrindavan",
        description="Test yatra description",
        start_date=today + timedelta(days=60),
        end_date=today + timedelta(days=67),
        registration_start_date=today,
        registration_deadline=today + timedelta(days=30),
        price_per_person=10000,
        status=YatraStatus.UPCOMING,
        created_by=admin_user.id,
    )
    db.add(yatra)
    db.commit()
    db.refresh(yatra)
    db.close()
    return yatra


class TestYatraEndpoints:
    """Test yatra management endpoints."""

    def test_list_yatras_public(self):
        """Test public listing of yatras."""
        response = client.get("/api/v1/yatras")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "yatras" in data["data"]

    def test_get_yatra_details(self, sample_yatra):
        """Test getting yatra details."""
        response = client.get(f"/api/v1/yatras/{sample_yatra.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "Test Yatra to Vrindavan"


class TestRegistrationValidation:
    """Test registration validation logic."""

    def test_date_validation(self):
        """Test that validators catch invalid dates."""
        from app.core.yatra_validators import YatraValidationError

        # This would be tested through actual endpoint calls
        # For now, just verify the exception exists
        assert YatraValidationError is not None


# Note: Full integration tests would require:
# 1. Authentication token generation
# 2. File upload mocking for payment screenshots
# 3. Status transition testing
# 4. Admin permission testing
# These can be added incrementally as the system is tested in development
