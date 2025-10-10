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

    # CORS
    allowed_origins: list = ["*"]
    allowed_methods: list = ["*"]
    allowed_headers: list = ["*"]

    # Security
    debug_db_token: str | None = None

    # Email Configuration
    mail_username: str = "test@example.com"
    mail_password: str = "test-password"
    mail_from: str = "test@example.com"
    mail_port: int = 587
    mail_server: str = "smtp.gmail.com"
    mail_starttls: bool = True
    mail_ssl_tls: bool = False
    mail_use_credentials: bool = True
    mail_validate_certs: bool = True

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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Map environment variable names to settings
        env_prefix = ""
        fields = {
            "jwt_secret_key": {"env": "JWT_SECRET_KEY"},
            "jwt_access_token_expire_minutes": {"env": "JWT_ACCESS_TOKEN_EXPIRE_MINUTES"},
            "max_upload_size_mb": {"env": "MAX_UPLOAD_SIZE_MB"},
            "mail_username": {"env": "MAIL_USERNAME"},
            "mail_password": {"env": "MAIL_PASSWORD"},
            "mail_from": {"env": "MAIL_FROM"},
            "mail_port": {"env": "MAIL_PORT"},
            "mail_server": {"env": "MAIL_SERVER"},
            "password_reset_token_expire_hours": {"env": "PASSWORD_RESET_TOKEN_EXPIRE_HOURS"},
            "password_reset_url_base": {"env": "PASSWORD_RESET_URL_BASE"},
            "email_verification_token_expire_hours": {
                "env": "EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS"
            },
            "email_verification_url_base": {"env": "EMAIL_VERIFICATION_URL_BASE"},
            "frontend_login_url": {"env": "FRONTEND_LOGIN_URL"},
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
