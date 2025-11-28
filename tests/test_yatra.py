"""
Basic tests for yatra registration system.

This module provides foundational tests for yatra and registration endpoints.
"""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.security import create_access_token
from app.db.models import Base, Devotee, UserRole, Yatra
from app.db.session import get_db
from main import app

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
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
        destination="Vrindavan",
        description="Test yatra description",
        start_date=today + timedelta(days=60),
        end_date=today + timedelta(days=67),
        registration_deadline=today + timedelta(days=50),
        is_active=True,
    )
    db.add(yatra)
    db.commit()
    db.refresh(yatra)
    db.close()
    return yatra


@pytest.fixture
def auth_headers(regular_user):
    """Generate authentication headers for testing."""
    token = create_access_token(data={"sub": regular_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers(admin_user):
    """Generate admin authentication headers for testing."""
    token = create_access_token(data={"sub": admin_user.email})
    return {"Authorization": f"Bearer {token}"}


class TestYatraEndpoints:
    """Test yatra management endpoints."""

    def test_list_yatras_requires_auth(self):
        """Test that listing yatras requires authentication."""
        response = client.get("/api/v1/yatras")
        assert response.status_code == 403  # Forbidden without auth

    def test_list_yatras_with_auth(self, auth_headers):
        """Test authenticated listing of yatras."""
        response = client.get("/api/v1/yatras", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "yatras" in data["data"]

    def test_get_yatra_details(self, sample_yatra, auth_headers):
        """Test getting yatra details with authentication."""
        response = client.get(f"/api/v1/yatras/{sample_yatra.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "Test Yatra to Vrindavan"


class TestYatraValidation:
    """Test yatra validation logic."""

    def test_date_validation_in_schema(self):
        """Test that schema validation catches invalid dates."""
        from pydantic import ValidationError

        from app.schemas.yatra import YatraCreate

        today = date.today()
        # Test past start_date
        with pytest.raises(ValidationError) as exc_info:
            YatraCreate(
                name="Test",
                destination="Test",
                start_date=today - timedelta(days=1),
                end_date=today + timedelta(days=7),
                registration_deadline=today + timedelta(days=5),
            )
        assert "start_date must be in the future" in str(exc_info.value)


# Note: Full integration tests would require:
# 1. Authentication token generation
# 2. File upload mocking for payment screenshots
# 3. Status transition testing
# 4. Admin permission testing
# These can be added incrementally as the system is tested in development
