"""
Application configuration management.

This module handles all configuration loading from environment variables,
provides validation, and sets up proper defaults for different environments.
"""

import json
import warnings
from functools import lru_cache
from urllib.parse import quote_plus

from pydantic import Field, field_validator
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
    database_url: str | None = None  # Full database URL (takes precedence if set)
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
    jwt_access_token_expire_minutes: int | None = None  # None = no expiration (token never expires)

    @field_validator("jwt_access_token_expire_minutes", mode="before")
    @classmethod
    def validate_jwt_expiration(cls, v):
        """Convert empty string to None for no expiration."""
        if v == "" or v is None:
            return None
        return int(v)

    # File Upload Configuration
    max_upload_size_mb: int = 20  # Total size limit per user
    max_file_size_mb: int = 10  # Individual file size limit
    max_files_per_user: int = 5  # Maximum number of files per user
    
    # Store as strings to prevent Pydantic Settings from trying to JSON parse
    # Use the properties below to get them as lists
    allowed_image_extensions_str: str = Field(
        default=".jpg,.jpeg,.png,.gif,.webp",
        alias="ALLOWED_IMAGE_EXTENSIONS"
    )
    allowed_document_extensions_str: str = Field(
        default=".pdf,.doc,.docx,.txt,.jpg,.jpeg,.png,.gif,.webp",
        alias="ALLOWED_DOCUMENT_EXTENSIONS"
    )

    @property
    def allowed_image_extensions(self) -> list[str]:
        """Get allowed image extensions as a list."""
        return self._parse_extensions(self.allowed_image_extensions_str)

    @property
    def allowed_document_extensions(self) -> list[str]:
        """Get allowed document extensions as a list."""
        return self._parse_extensions(self.allowed_document_extensions_str)

    def _parse_extensions(self, value: str) -> list[str]:
        """Parse extension string into list. Handles JSON or comma-separated."""
        if not value or not value.strip():
            return []
        value = value.strip()
        # Try JSON first
        if value.startswith('['):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass
        # Fall back to comma-separated
        return [x.strip() for x in value.split(',') if x.strip()]

    # Google Cloud Storage Configuration
    gcs_bucket_name: str = "uddhava-user-files"
    gcs_project_id: str = "potent-poet-474916-a8"
    use_gcs: bool = True  # Always use GCS for file storage

    # CORS - Allowed origins for production and development
    allowed_origins: list = [
        "https://rsyatra.com",  # Production frontend (custom domain)
        "https://www.rsyatra.com",  # Production frontend with www (custom domain)
        "https://rsyatra.onrender.com",  # Production frontend (Render subdomain - legacy)
        "https://dev-rsyatra.onrender.com",  # Development frontend (Render subdomain)
        "http://localhost:1728",  # Local frontend for development
        "http://localhost:8000",  # Backend testing
    ]
    allowed_methods: list = ["*"]
    allowed_headers: list = ["*"]

    # Security
    debug_db_token: str | None = None

    # SMTP Configuration (Hostinger)
    SMTP_HOST: str = "smtp.hostinger.com"
    SMTP_PORT: int = 587  # TLS/STARTTLS port
    SMTP_USER: str = "info@rsyatra.com"
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "info@rsyatra.com"

    # Frontend URLs
    FRONTEND_URL: str = "http://localhost:5173"  # Development Vite frontend
    frontend_login_url: str = "https://rsyatra.com/login"
    frontend_base_url: str = "https://rsyatra.com"

    # Support Contact
    support_email: str = "radhashyamsundaryatra@gmail.com"

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

    def get_database_url(self) -> str:
        """
        Get database URL, either from DATABASE_URL env var or construct from components.

        Priority:
        1. DATABASE_URL environment variable (if set)
        2. Constructed from db_host, db_port, db_user, db_password, db_name
        """
        if self.database_url:
            return self.database_url

        # Fallback: construct from individual components
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

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "populate_by_name": True,  # Allow both alias and field name
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
