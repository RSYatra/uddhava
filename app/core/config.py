"""
Application configuration management.

This module handles all configuration loading from environment variables,
provides validation, and sets up proper defaults for different environments.
"""

import warnings
from functools import lru_cache
from typing import Optional

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

    # File Upload
    max_upload_size_mb: int = 10
    upload_directory: str = "static"
    allowed_extensions: list = [".jpg", ".jpeg", ".png", ".gif", ".bmp"]

    # CORS
    allowed_origins: list = ["*"]
    allowed_methods: list = ["*"]
    allowed_headers: list = ["*"]

    # Security
    debug_db_token: Optional[str] = None

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
        from urllib.parse import quote_plus

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
        """Get max upload size in bytes."""
        return self.max_upload_size_mb * 1024 * 1024

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Map environment variable names to settings
        env_prefix = ""
        fields = {
            "jwt_secret_key": {"env": "JWT_SECRET_KEY"},
            "jwt_access_token_expire_minutes": {
                "env": "JWT_ACCESS_TOKEN_EXPIRE_MINUTES"
            },
            "max_upload_size_mb": {"env": "MAX_UPLOAD_SIZE_MB"},
        }


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached application settings.

    Returns:
        Settings: Application configuration object
    """
    return Settings()


# Export commonly used settings
settings = get_settings()
