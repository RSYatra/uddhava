"""
Enhanced security utilities for devotee authentication.

This module provides additional security measures specifically for devotee
authentication including rate limiting, input validation, and secure error handling.
"""

import hashlib
import logging
import re
import secrets
import time
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, Request, status
from pydantic import BaseModel, EmailStr, ValidationError

logger = logging.getLogger(__name__)


class AuthSecurityManager:
    """
    Manages authentication security features including rate limiting and brute force protection.
    """

    def __init__(self):
        # In-memory storage for rate limiting (use Redis in production)
        self._login_attempts: dict[str, list] = {}
        self._signup_attempts: dict[str, list] = {}
        self._password_reset_attempts: dict[str, list] = {}
        self._blocked_ips: dict[str, datetime] = {}

        # Security configuration
        self.MAX_LOGIN_ATTEMPTS = 5
        self.MAX_SIGNUP_ATTEMPTS = 3
        self.MAX_PASSWORD_RESET_ATTEMPTS = 3
        self.RATE_LIMIT_WINDOW = 900  # 15 minutes
        self.BLOCK_DURATION = 3600  # 1 hour
        self.LOGIN_ATTEMPT_WINDOW = 300  # 5 minutes

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for real IP in headers (for proxies/load balancers)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        return request.client.host if request.client else "unknown"

    def _clean_old_attempts(self, attempts_dict: dict[str, list], window: int):
        """Remove old attempts outside the time window."""
        current_time = time.time()
        for key in list(attempts_dict.keys()):
            attempts_dict[key] = [
                timestamp for timestamp in attempts_dict[key] if current_time - timestamp < window
            ]
            if not attempts_dict[key]:
                del attempts_dict[key]

    def _is_ip_blocked(self, ip: str) -> bool:
        """Check if IP is currently blocked."""
        if ip in self._blocked_ips:
            if datetime.now(UTC) < self._blocked_ips[ip]:
                return True
            del self._blocked_ips[ip]
        return False

    def _block_ip(self, ip: str, duration_seconds: int = None):
        """Block IP address for specified duration."""
        duration = duration_seconds or self.BLOCK_DURATION
        block_until = datetime.now(UTC) + timedelta(seconds=duration)
        self._blocked_ips[ip] = block_until
        logger.warning(f"Blocked IP {ip} until {block_until}")

    def check_login_rate_limit(self, request: Request, email: str) -> None:
        """Check and enforce login rate limiting."""
        ip = self._get_client_ip(request)
        current_time = time.time()

        # Check if IP is blocked
        if self._is_ip_blocked(ip):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="IP address temporarily blocked due to suspicious activity",
            )

        # Clean old attempts
        self._clean_old_attempts(self._login_attempts, self.LOGIN_ATTEMPT_WINDOW)

        # Create composite key (IP + email hash for privacy)
        email_hash = hashlib.sha256(email.lower().encode()).hexdigest()[:8]
        key = f"{ip}:{email_hash}"

        # Check attempts
        if key not in self._login_attempts:
            self._login_attempts[key] = []

        if len(self._login_attempts[key]) >= self.MAX_LOGIN_ATTEMPTS:
            # Block IP after too many attempts
            self._block_ip(ip)
            logger.warning(
                f"Blocking IP {ip} after {self.MAX_LOGIN_ATTEMPTS} failed login attempts"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Please try again later.",
            )

        # Record this attempt
        self._login_attempts[key].append(current_time)

    def check_signup_rate_limit(self, request: Request) -> None:
        """Check and enforce signup rate limiting."""
        ip = self._get_client_ip(request)
        current_time = time.time()

        if self._is_ip_blocked(ip):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="IP address temporarily blocked",
            )

        self._clean_old_attempts(self._signup_attempts, self.RATE_LIMIT_WINDOW)

        if ip not in self._signup_attempts:
            self._signup_attempts[ip] = []

        if len(self._signup_attempts[ip]) >= self.MAX_SIGNUP_ATTEMPTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many signup attempts from this IP. Please try again later.",
            )

        self._signup_attempts[ip].append(current_time)

    def check_password_reset_rate_limit(self, request: Request, email: str) -> None:
        """Check and enforce password reset rate limiting."""
        ip = self._get_client_ip(request)
        current_time = time.time()

        if self._is_ip_blocked(ip):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="IP address temporarily blocked",
            )

        self._clean_old_attempts(self._password_reset_attempts, self.RATE_LIMIT_WINDOW)

        email_hash = hashlib.sha256(email.lower().encode()).hexdigest()[:8]
        key = f"{ip}:{email_hash}"

        if key not in self._password_reset_attempts:
            self._password_reset_attempts[key] = []

        if len(self._password_reset_attempts[key]) >= self.MAX_PASSWORD_RESET_ATTEMPTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many password reset attempts. Please try again later.",
            )

        self._password_reset_attempts[key].append(current_time)

    def record_successful_login(self, request: Request, email: str) -> None:
        """Clear login attempts after successful login."""
        ip = self._get_client_ip(request)
        email_hash = hashlib.sha256(email.lower().encode()).hexdigest()[:8]
        key = f"{ip}:{email_hash}"

        if key in self._login_attempts:
            del self._login_attempts[key]


# Global security manager instance
auth_security = AuthSecurityManager()


class InputValidator:
    """Validates and sanitizes user inputs for security."""

    # Dangerous patterns that could indicate injection attempts
    DANGEROUS_PATTERNS = [
        r"<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>",  # Script tags
        r"javascript:",  # JavaScript protocol
        r"vbscript:",  # VBScript protocol
        r"on\w+\s*=",  # Event handlers
        r"<iframe\b",  # Iframe tags
        r"<object\b",  # Object tags
        r"<embed\b",  # Embed tags
        r"<link\b",  # Link tags
        r"<meta\b",  # Meta tags
        r"<base\b",  # Base tags
        r"<form\b",  # Form tags
        r"<input\b",  # Input tags
        r"<textarea\b",  # Textarea tags
        r"<select\b",  # Select tags
        r"<button\b",  # Button tags
        r"data:text/html",  # Data URL with HTML
        r"(union|select|insert|update|delete|drop|create|alter|exec|execute)\s+",  # SQL keywords
    ]

    @staticmethod
    def sanitize_string(value: str, max_length: int = 255) -> str:
        """Sanitize string input by removing dangerous content."""
        if not value:
            return ""

        # Truncate to max length
        value = value[:max_length]

        # Remove null bytes
        value = value.replace("\x00", "")

        # Check for dangerous patterns
        for pattern in InputValidator.DANGEROUS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                logger.warning(f"Dangerous pattern detected in input: {pattern}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid input detected",
                )

        # HTML encode dangerous characters
        value = (
            value.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )

        return value.strip()

    @staticmethod
    def validate_email(email: str) -> str:
        """Validate and normalize email address."""
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is required",
            )

        # Basic length check
        if len(email) > 320:  # RFC 5321 limit
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email address too long",
            )

        # Normalize email (lowercase, strip whitespace)
        email = email.lower().strip()

        # Validate email format using Pydantic
        try:

            class EmailValidator(BaseModel):
                email: EmailStr

            EmailValidator(email=email)
        except ValidationError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format",
            ) from None

        # Additional security checks
        if ".." in email or email.startswith(".") or email.endswith("."):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format",
            )

        return email

    @staticmethod
    def validate_password(password: str) -> str:
        """Validate password strength and security."""
        if not password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password is required",
            )

        # Length requirements
        if len(password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long",
            )

        if len(password) > 128:  # Prevent DoS attacks
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password too long",
            )

        # Complexity requirements
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

        if not (has_upper and has_lower and has_digit and has_special):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must contain uppercase, lowercase, digit, and special character",
            )

        # Check for common patterns
        if password.lower() in [
            "password",
            "12345678",
            "qwerty123",
            "admin123",
        ]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password is too common",
            )

        return password

    @staticmethod
    def validate_phone_number(phone: str) -> str:
        """Validate and sanitize phone number."""
        if not phone:
            return ""

        # Remove all non-digit characters
        digits_only = re.sub(r"\D", "", phone)

        # Check length (minimum 10 digits, maximum 15 for international)
        if len(digits_only) < 10 or len(digits_only) > 15:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid phone number format",
            )

        return digits_only


class SecureTokenManager:
    """Manages secure token generation and validation."""

    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """Generate cryptographically secure token."""
        return secrets.token_urlsafe(length)

    @staticmethod
    def generate_verification_token(email: str) -> str:
        """Generate email verification token with embedded email hash."""
        # Create a token that includes email verification but doesn't expose email
        email_hash = hashlib.sha256(email.lower().encode()).hexdigest()[:16]
        random_part = secrets.token_urlsafe(24)

        # Combine parts with timestamp for uniqueness
        timestamp = str(int(time.time()))
        return f"{random_part}.{timestamp}.{email_hash}"

    @staticmethod
    def validate_token_format(token: str) -> bool:
        """Validate token format to prevent injection attacks."""
        if not token:
            return False

        # Check length (prevent extremely long tokens)
        if len(token) > 200:
            return False

        # Check for dangerous characters
        if any(char in token for char in ["<", ">", '"', "'", "&", "\x00"]):
            return False

        # Must be URL-safe base64 or similar format
        if not re.match(r"^[A-Za-z0-9_\-\.]+$", token):
            return False

        return True


class ErrorHandler:
    """Handles secure error responses that don't leak sensitive information."""

    @staticmethod
    def safe_error_response(error_type: str, detail: str = None) -> HTTPException:
        """Generate safe error response without information leakage."""
        safe_messages = {
            "auth_failed": "Invalid credentials",
            "user_not_found": "Invalid credentials",  # Don't reveal user existence
            "token_invalid": "Invalid or expired token",
            "token_expired": "Token has expired",
            "rate_limited": "Too many requests. Please try again later.",
            "validation_failed": "Invalid input provided",
            "server_error": "An error occurred. Please try again later.",
            "forbidden": "Access denied",
            "not_found": "Resource not found",
        }

        safe_detail = safe_messages.get(error_type, "An error occurred")

        status_codes = {
            "auth_failed": status.HTTP_401_UNAUTHORIZED,
            "user_not_found": status.HTTP_401_UNAUTHORIZED,
            "token_invalid": status.HTTP_401_UNAUTHORIZED,
            "token_expired": status.HTTP_401_UNAUTHORIZED,
            "rate_limited": status.HTTP_429_TOO_MANY_REQUESTS,
            "validation_failed": status.HTTP_400_BAD_REQUEST,
            "server_error": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "forbidden": status.HTTP_403_FORBIDDEN,
            "not_found": status.HTTP_404_NOT_FOUND,
        }

        status_code = status_codes.get(error_type, status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Log the actual error for debugging but don't expose it
        if detail:
            logger.error(f"Error ({error_type}): {detail}")

        return HTTPException(status_code=status_code, detail=safe_detail)


# Global instances
input_validator = InputValidator()
token_manager = SecureTokenManager()
error_handler = ErrorHandler()
