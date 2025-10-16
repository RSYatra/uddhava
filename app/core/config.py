"""
Application configuration management.

This module handles all configuration loading from environment variables,
provides validation, and sets up proper defaults for different environments.
"""

import warnings
from functools import lru_cache
from urllib.parse import quote_plus

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Application
    app_name: str = "Uddhava API"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"  # nosec: B104 - Intentional for containerized deployment
    port: int = 8000
    workers: int = 1

    # Database
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "root"
    db_password: str = "changeme"
    db_name: str = "uddhava_db"

    # Database Connection Pool Settings
    db_pool_size: int = 10  # Base number of connections in pool
    db_max_overflow: int = 20  # Additional connections when pool is full
    db_pool_timeout: int = 30  # Seconds to wait for connection from pool
    db_pool_recycle: int = 1800  # Recycle connections after 30 minutes (prevent timeout)
    db_pool_pre_ping: bool = True  # Test connections before using them
    db_connect_timeout: int = 10  # Seconds to wait for initial connection
    db_read_timeout: int = 30  # Seconds to wait for query results
    db_write_timeout: int = 30  # Seconds to wait for write operations

    # Database Retry Settings
    db_max_retries: int = 3  # Maximum retry attempts for failed operations
    db_retry_delay: float = 1.0  # Initial delay between retries (seconds)
    db_retry_backoff: float = 2.0  # Exponential backoff multiplier

    # JWT Authentication
    jwt_secret_key: str = "your-secret-key-change-this-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30

    # File Upload Configuration
    max_upload_size_mb: int = 20  # Total size limit per user
    max_file_size_mb: int = 5  # Individual file size limit
    max_files_per_user: int = 5  # Maximum number of files per user
    upload_directory: str = "uploads"  # Base directory for uploads
    allowed_image_extensions: list = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
    # Documents can be PDFs, Office docs, text files, or images (for scanned documents)
    allowed_document_extensions: list = [
        ".pdf",
        ".doc",
        ".docx",
        ".txt",
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
    ]

    # CORS - Allowed origins for production and development
    allowed_origins: list = [
        "https://rsyatra.onrender.com",  # Production frontend
        "http://localhost:1728",  # Local frontend for development
        "http://localhost:8000",  # Backend testing
    ]
    allowed_methods: list = ["*"]
    allowed_headers: list = ["*"]

    # Security
    debug_db_token: str | None = None

    # Email Configuration (Gmail API with OAuth2)
    # With token.json present: Real emails sent via Gmail API (dev and prod)
    # Without token.json: Emails logged to console (dev only, production fails)
    gmail_credentials_file: str = "token.json"  # OAuth2 credentials (token.json or token.pickle)
    gmail_from_email: str = "test@example.com"  # Gmail sender address
    gmail_from_name: str = "Radha Shyam Sundar Seva"  # Display name in emails

    # Password Reset
    password_reset_token_expire_hours: int = 1
    password_reset_url_base: str = "https://rsyatra.com/reset-password"

    # Email Verification
    email_verification_token_expire_hours: int = 24
    email_verification_url_base: str = "https://rsyatra.com/verify-email"

    # Frontend URLs
    frontend_login_url: str = "https://rsyatra.com/login"

    @field_validator("jwt_secret_key")
    def validate_jwt_secret(cls, v):
        """Warn if using default secret key."""
        if v == "your-secret-key-change-this-in-production":
            warnings.warn(
                "Using default JWT secret key! This is insecure for production. "
                "Set JWT_SECRET_KEY environment variable to a secure random string. "
                "Generate one with: openssl rand -hex 32",
                UserWarning,
                stacklevel=3,
            )
        return v

    @field_validator("environment")
    def validate_environment(cls, v):
        """Validate environment setting."""
        valid_envs = ["development", "testing", "staging", "production"]
        if v.lower() not in valid_envs:
            raise ValueError(f"Environment must be one of: {valid_envs}")
        return v.lower()

    @property
    def database_url(self) -> str:
        """Construct database URL with proper URL encoding for special characters."""
        # URL encode the password to handle special characters like @
        encoded_pwd = quote_plus(self.db_password)  # Not a hardcoded password
        encoded_user = quote_plus(self.db_user)

        return (
            f"mysql+pymysql://{encoded_user}:{encoded_pwd}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"

    @property
    def max_upload_size_bytes(self) -> int:
        """Get max total upload size in bytes."""
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def max_file_size_bytes(self) -> int:
        """Get max individual file size in bytes."""
        return self.max_file_size_mb * 1024 * 1024

    @property
    def all_allowed_extensions(self) -> list[str]:
        """Get all allowed file extensions."""
        return self.allowed_image_extensions + self.allowed_document_extensions

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    """
    Get cached application settings.

    Returns:
        Settings: Application configuration object
    """
    return Settings()


# Export commonly used settings
settings = get_settings()
