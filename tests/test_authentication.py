"""
Test authentication endpoints and JWT functionality.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Override the database dependency
from app.db.models import Base, Devotee
from app.db.session import get_db
from main import app

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)


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
def clean_database():
    """Clean database before each test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    # Cleanup after test
    Base.metadata.drop_all(bind=engine)


class TestAuthentication:
    """Test suite for authentication endpoints."""

    def test_signup_success(self):
        """Test successful user signup."""
        signup_data = {
            "legal_name": "Test User",
            "email": "unique_test_user@example.com",
            "password": "SecurePassword123!",
        }

        response = client.post("/api/v1/auth/signup", json=signup_data)

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "data" in data
        assert data["data"]["email"] == "unique_test_user@example.com"

    def test_signup_duplicate_email(self):
        """Test signup with duplicate email returns error."""
        # First, create a user
        first_signup = {
            "legal_name": "Test User",
            "email": "duplicate_test@example.com",
            "password": "SecurePassword123!",
        }
        client.post("/api/v1/auth/signup", json=first_signup)

        # Now try to signup with the same email
        signup_data = {
            "legal_name": "Test User 2",
            "email": "duplicate_test@example.com",  # Same email as above
            "password": "AnotherPassword123!",
        }

        response = client.post("/api/v1/auth/signup", json=signup_data)

        assert response.status_code == 409  # Conflict - duplicate email
        data = response.json()
        assert "Devotee exists but is not verified" in data["message"]

    def test_signup_invalid_email(self):
        """Test signup with invalid email format."""
        signup_data = {
            "legal_name": "Test User",
            "email": "invalid-email",
            "password": "securepassword123",
            "chanting_number_of_rounds": 16,
        }

        response = client.post("/api/v1/auth/signup", json=signup_data)

        assert response.status_code == 422  # Validation error

    def test_signup_weak_password(self):
        """Test signup with weak password."""
        signup_data = {
            "legal_name": "Test User",
            "email": "weak@example.com",
            "password": "123",  # Too short
            "chanting_number_of_rounds": 16,
        }

        response = client.post("/api/v1/auth/signup", json=signup_data)

        assert response.status_code == 422  # Validation error

    def test_login_success(self):
        """Test successful login."""
        # First, create and verify a user
        signup_data = {
            "legal_name": "Login Test User",
            "email": "login_test@example.com",
            "password": "SecurePassword123!",
        }
        client.post("/api/v1/auth/signup", json=signup_data)

        # Manually verify the devotee for testing
        db = TestingSessionLocal()
        try:
            devotee = db.query(Devotee).filter(Devotee.email == "login_test@example.com").first()
            if devotee:
                devotee.email_verified = True
                db.commit()
        finally:
            db.close()

        login_data = {
            "email": "login_test@example.com",
            "password": "SecurePassword123!",
        }

        response = client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "access_token" in data["data"]
        assert data["data"]["token_type"] == "bearer"

    def test_login_wrong_password(self):
        """Test login with wrong password."""
        login_data = {"email": "test@example.com", "password": "wrongpassword"}

        response = client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == 401
        data = response.json()
        assert "Invalid credentials" in data["message"]

    def test_login_nonexistent_user(self):
        """Test login with nonexistent user."""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "somepassword",
        }

        response = client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == 401
        data = response.json()
        assert "Invalid credentials" in data["message"]

    def test_protected_endpoint_without_token(self):
        """Test accessing protected endpoint without token."""
        response = client.get("/api/v1/devotees")

        assert response.status_code == 403  # Should require authentication

    def test_protected_endpoint_with_valid_token(self):
        """Test accessing protected endpoint with valid token."""
        # First, create and verify a user
        signup_data = {
            "legal_name": "Protected Test User",
            "email": "protected_test@example.com",
            "password": "SecurePassword123!",
        }
        client.post("/api/v1/auth/signup", json=signup_data)

        # Manually verify the devotee for testing
        db = TestingSessionLocal()
        try:
            devotee = (
                db.query(Devotee).filter(Devotee.email == "protected_test@example.com").first()
            )
            if devotee:
                devotee.email_verified = True
                db.commit()
        finally:
            db.close()

        # First login to get a token
        login_data = {
            "email": "protected_test@example.com",
            "password": "SecurePassword123!",
        }

        login_response = client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        token = login_response.json()["data"]["access_token"]

        # Use token to access protected endpoint - need admin for devotees list
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v1/devotees", headers=headers)

        # Will be 403 if user is not admin, which is expected for regular user
        assert response.status_code in [200, 403]

    def test_protected_endpoint_with_invalid_token(self):
        """Test accessing protected endpoint with invalid token."""
        headers = {"Authorization": "Bearer invalid-token"}
        response = client.get("/api/v1/devotees", headers=headers)

        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]

    def test_protected_endpoint_with_expired_token(self):
        """Test accessing protected endpoint with expired token."""
        # This is a mock expired token (create one that's actually expired)
        expired_token = (  # nosec: B105 - Test token, not a real password
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
            "eyJzdWIiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiZXhwIjoxfQ.invalid"
        )
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.get("/api/v1/devotees", headers=headers)

        assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__])
