"""
Security configuration for the devotee authentication system.

This module contains all security-related constants, configurations,
and utilities to ensure consistent security practices across the application.
"""

import secrets
from enum import Enum


class SecurityLevel(Enum):
    """Security levels for different operations."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityConfig:
    """
    Centralized security configuration for the application.

    Contains all security-related constants and settings to ensure
    consistent security practices across the entire application.
    """

    # Rate limiting configurations
    RATE_LIMITS = {
        "login": {"calls": 5, "period": 900},  # 5 attempts per 15 minutes
        "signup": {"calls": 3, "period": 900},  # 3 attempts per 15 minutes
        "password_reset": {
            "calls": 3,
            "period": 1800,
        },  # 3 attempts per 30 minutes
        "email_verification": {
            "calls": 5,
            "period": 1800,
        },  # 5 attempts per 30 minutes
        "general": {"calls": 100, "period": 60},  # 100 requests per minute
    }

    # Suspicious activity thresholds
    SUSPICIOUS_ACTIVITY_THRESHOLD = 5
    SUSPICIOUS_ACTIVITY_WINDOW = 3600  # 1 hour

    # Request size limits (in bytes)
    MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10 MB
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

    # HTTP status codes for security responses
    HTTP_BAD_REQUEST = 400
    HTTP_UNAUTHORIZED = 401
    HTTP_FORBIDDEN = 403
    HTTP_TOO_MANY_REQUESTS = 429
    HTTP_REQUEST_TOO_LARGE = 413

    # Token configurations
    TOKEN_LENGTH = 32
    VERIFICATION_TOKEN_EXPIRY = 86400  # 24 hours
    PASSWORD_RESET_TOKEN_EXPIRY = 3600  # 1 hour
    REFRESH_TOKEN_EXPIRY = 604800  # 7 days

    # Password configurations
    MIN_PASSWORD_LENGTH = 8
    MAX_PASSWORD_LENGTH = 128
    PASSWORD_COMPLEXITY_PATTERNS = [
        r"[a-z]",  # lowercase
        r"[A-Z]",  # uppercase
        r"\d",  # digit
        r"[!@#$%^&*(),.?\":{}|<>]",  # special character
    ]

    # File upload security
    ALLOWED_FILE_TYPES = {
        "image": {".jpg", ".jpeg", ".png", ".gif", ".webp"},
        "document": {".pdf", ".doc", ".docx", ".txt"},
    }
    DANGEROUS_FILE_EXTENSIONS = {
        ".exe",
        ".bat",
        ".cmd",
        ".com",
        ".pif",
        ".scr",
        ".vbs",
        ".js",
        ".jar",
        ".php",
        ".py",
        ".rb",
        ".sh",
        ".asp",
        ".aspx",
        ".jsp",
    }

    # Suspicious user agents (lowercase)
    SUSPICIOUS_USER_AGENTS = {
        "bot",
        "crawler",
        "spider",
        "scraper",
        "curl",
        "wget",
        "python-requests",
        "http",
        "scanner",
        "test",
        "automated",
    }

    # Attack patterns for detection
    ATTACK_PATTERNS = {
        "sql_injection": [
            "union select",
            "drop table",
            "insert into",
            "delete from",
            "update set",
            "alter table",
            "create table",
            "exec(",
            "execute(",
            "sp_",
            "xp_",
            "0x",
            "char(",
            "ascii(",
        ],
        "xss": [
            "<script",
            "javascript:",
            "onerror=",
            "onload=",
            "onclick=",
            "onmouseover=",
            "onfocus=",
            "onblur=",
            "onchange=",
            "eval(",
            "document.cookie",
            "document.write",
        ],
        "path_traversal": [
            "../",
            "..\\",
            "..\\/",
            "....//",
            "....\\\\",
            "%2e%2e%2f",
            "%2e%2e\\",
            "%252e%252e%252f",
        ],
        "command_injection": [
            "; cat ",
            "| nc ",
            "&& curl",
            "|| wget",
            "; rm ",
            "| bash",
            "&& bash",
            "; sh",
            "| sh",
            "`",
            "$(",
        ],
        "ldap_injection": [
            "*)(uid=",
            "*)(cn=",
            "*)(&",
            "*))%00",
            "admin*",
            "*)(objectclass=*",
        ],
    }

    # Security headers configuration
    SECURITY_HEADERS = {
        # Core security headers
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": (
            "geolocation=(), microphone=(), camera=(), "
            "payment=(), usb=(), magnetometer=(), gyroscope=()"
        ),
        # HSTS (Strict Transport Security)
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
        # Cross-Origin policies
        "Cross-Origin-Embedder-Policy": "require-corp",
        "Cross-Origin-Opener-Policy": "same-origin",
        "Cross-Origin-Resource-Policy": "same-origin",
        # Additional security
        "X-Permitted-Cross-Domain-Policies": "none",
        "X-Download-Options": "noopen",
    }

    # Content Security Policy
    CSP_POLICY = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "object-src 'none'; "
        "media-src 'self'"
    )

    # Cache control for auth endpoints
    AUTH_CACHE_HEADERS = {
        "Cache-Control": "no-store, no-cache, must-revalidate, private",
        "Pragma": "no-cache",
        "Expires": "0",
    }

    # Trusted domains for CORS
    TRUSTED_ORIGINS = {
        "development": ["http://localhost:3000", "http://localhost:8000"],
        "production": [],  # Will be configured based on deployment
    }

    # IP whitelist for admin operations (empty means no restriction)
    ADMIN_IP_WHITELIST: set[str] = set()

    # Blocked IP addresses (can be populated from threat intelligence)
    BLOCKED_IPS: set[str] = set()

    # Session security
    SESSION_COOKIE_SECURE = True  # HTTPS only
    SESSION_COOKIE_HTTPONLY = True  # No JS access
    SESSION_COOKIE_SAMESITE = "Lax"  # CSRF protection
    SESSION_MAX_AGE = 86400  # 24 hours

    # JWT security
    JWT_ALGORITHM = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7

    # Logging configuration for security events
    SECURITY_LOG_EVENTS = {
        "failed_login",
        "suspicious_activity",
        "rate_limit_exceeded",
        "invalid_token",
        "privilege_escalation_attempt",
        "file_upload_rejected",
        "attack_pattern_detected",
    }


class SecurityUtils:
    """Utility functions for security operations."""

    @staticmethod
    def generate_secure_token(
        length: int = SecurityConfig.TOKEN_LENGTH,
    ) -> str:
        """Generate a cryptographically secure random token."""
        return secrets.token_urlsafe(length)

    @staticmethod
    def is_safe_filename(filename: str) -> bool:
        """Check if filename is safe for upload."""
        if not filename:
            return False

        # Check for dangerous extensions
        lower_filename = filename.lower()
        for ext in SecurityConfig.DANGEROUS_FILE_EXTENSIONS:
            if lower_filename.endswith(ext):
                return False

        # Check for path traversal attempts
        if ".." in filename or "/" in filename or "\\" in filename:
            return False

        return True

    @staticmethod
    def detect_attack_patterns(text: str) -> list[str]:
        """Detect attack patterns in text and return detected pattern types."""
        detected_patterns = []
        text_lower = text.lower()

        for pattern_type, patterns in SecurityConfig.ATTACK_PATTERNS.items():
            for pattern in patterns:
                if pattern in text_lower:
                    detected_patterns.append(pattern_type)
                    break  # One detection per type is enough

        return detected_patterns

    @staticmethod
    def is_suspicious_user_agent(user_agent: str) -> bool:
        """Check if user agent appears suspicious."""
        if not user_agent:
            return True

        user_agent_lower = user_agent.lower()
        return any(
            suspicious in user_agent_lower for suspicious in SecurityConfig.SUSPICIOUS_USER_AGENTS
        )

    @staticmethod
    def sanitize_error_message(error_msg: str, security_level: SecurityLevel) -> str:
        """Sanitize error messages based on security level."""
        if security_level == SecurityLevel.CRITICAL:
            return "Operation failed"
        if security_level == SecurityLevel.HIGH:
            return "Authentication failed"
        if security_level == SecurityLevel.MEDIUM:
            # Remove sensitive information but keep basic error info
            sensitive_terms = ["password", "token", "key", "secret", "admin"]
            sanitized = error_msg
            for term in sensitive_terms:
                sanitized = sanitized.replace(term, "***")
            return sanitized
        # LOW security level
        return error_msg


# Global security configuration instance
security_config = SecurityConfig()
security_utils = SecurityUtils()
