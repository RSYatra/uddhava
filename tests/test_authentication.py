"""
Test authentication endpoints and JWT functionality.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base
from main import app, get_db

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
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


class TestAuthentication:
    """Test suite for authentication endpoints."""

    def test_signup_success(self):
        """Test successful user signup."""
        signup_data = {
            "name": "Test User",
            "email": "test@example.com",
            "password": "securepassword123",
            "chanting_rounds": 16,
        }

        response = client.post("/auth/signup", json=signup_data)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data

    def test_signup_duplicate_email(self):
        """Test signup with duplicate email returns error."""
        signup_data = {
            "name": "Test User 2",
            "email": "test@example.com",  # Same email as above
            "password": "anotherpassword123",
            "chanting_rounds": 8,
        }

        response = client.post("/auth/signup", json=signup_data)

        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]

    def test_signup_invalid_email(self):
        """Test signup with invalid email format."""
        signup_data = {
            "name": "Test User",
            "email": "invalid-email",
            "password": "securepassword123",
            "chanting_rounds": 16,
        }

        response = client.post("/auth/signup", json=signup_data)

        assert response.status_code == 422  # Validation error

    def test_signup_weak_password(self):
        """Test signup with weak password."""
        signup_data = {
            "name": "Test User",
            "email": "weak@example.com",
            "password": "123",  # Too short
            "chanting_rounds": 16,
        }

        response = client.post("/auth/signup", json=signup_data)

        assert response.status_code == 422  # Validation error

    def test_login_success(self):
        """Test successful login."""
        login_data = {
            "email": "test@example.com",
            "password": "securepassword123",
        }

        response = client.post("/auth/login", json=login_data)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self):
        """Test login with wrong password."""
        login_data = {"email": "test@example.com", "password": "wrongpassword"}

        response = client.post("/auth/login", json=login_data)

        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]

    def test_login_nonexistent_user(self):
        """Test login with nonexistent user."""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "somepassword",
        }

        response = client.post("/auth/login", json=login_data)

        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]

    def test_protected_endpoint_without_token(self):
        """Test accessing protected endpoint without token."""
        response = client.get("/users")

        assert response.status_code == 403  # Should require authentication

    def test_protected_endpoint_with_valid_token(self):
        """Test accessing protected endpoint with valid token."""
        # First login to get a token
        login_data = {
            "email": "test@example.com",
            "password": "securepassword123",
        }

        login_response = client.post("/auth/login", json=login_data)
        token = login_response.json()["access_token"]

        # Use token to access protected endpoint
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/users", headers=headers)

        assert response.status_code == 200
        users = response.json()
        assert isinstance(users, list)

    def test_protected_endpoint_with_invalid_token(self):
        """Test accessing protected endpoint with invalid token."""
        headers = {"Authorization": "Bearer invalid-token"}
        response = client.get("/users", headers=headers)

        assert response.status_code == 401
        assert "Invalid authentication credentials" in response.json()["detail"]

    def test_protected_endpoint_with_expired_token(self):
        """Test accessing protected endpoint with expired token."""
        # This is a mock expired token (create one that's actually expired)
        expired_token = (  # nosec: B105 - Test token, not a real password
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
            "eyJzdWIiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiZXhwIjoxfQ.invalid"
        )
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.get("/users", headers=headers)

        assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__])
