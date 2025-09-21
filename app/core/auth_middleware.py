"""
Enhanced security middleware for devotee authentication endpoints.

This module provides additional security measures beyond the base middleware,
specifically designed for protecting authentication-related endpoints.
"""

import logging
import time
from typing import Callable

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class AuthSecurityMiddleware(BaseHTTPMiddleware):
    """
    Enhanced security middleware specifically for authentication endpoints.

    Provides additional security measures including:
    - Enhanced rate limiting for auth endpoints
    - Request size limiting
    - Suspicious activity detection
    - Additional security headers
    """

    def __init__(self, app):
        super().__init__(app)
        self.auth_endpoints = {
            "/api/v1/devotees/auth/signup",
            "/api/v1/devotees/auth/login",
            "/api/v1/devotees/auth/forgot-password",
            "/api/v1/devotees/auth/reset-password",
            "/api/v1/devotees/auth/verify-email",
            "/api/v1/devotees/auth/resend-verification",
        }
        # Track suspicious patterns
        self.suspicious_activity = {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply enhanced security checks for auth endpoints."""

        # Check if this is an auth endpoint
        if request.url.path in self.auth_endpoints:
            await self._apply_auth_security_checks(request)

        # Continue with request processing
        response = await call_next(request)

        # Add additional security headers for auth endpoints
        if request.url.path in self.auth_endpoints:
            self._add_auth_security_headers(response)

        return response

    async def _apply_auth_security_checks(self, request: Request):
        """Apply security checks specific to auth endpoints."""

        # 1. Request size limiting
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 10 * 1024 * 1024:  # 10MB limit
            logger.warning(
                f"Request too large: {content_length} bytes from {request.client.host}"
            )
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Request too large",
            )

        # 2. Check for suspicious user agents
        user_agent = request.headers.get("user-agent", "").lower()
        suspicious_agents = [
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
        ]

        if any(agent in user_agent for agent in suspicious_agents):
            client_ip = self._get_client_ip(request)
            logger.warning(f"Suspicious user agent from {client_ip}: {user_agent}")

            # Track suspicious activity
            if client_ip not in self.suspicious_activity:
                self.suspicious_activity[client_ip] = {
                    "count": 0,
                    "first_seen": time.time(),
                }

            self.suspicious_activity[client_ip]["count"] += 1

            # Block if too many suspicious requests
            if self.suspicious_activity[client_ip]["count"] > 5:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied",
                )

        # 3. Check for common attack patterns in headers
        self._check_attack_patterns(request)

        # 4. Validate content type for POST requests
        if request.method == "POST":
            content_type = request.headers.get("content-type", "")
            if not (
                content_type.startswith("application/json")
                or content_type.startswith("application/x-www-form-urlencoded")
                or content_type.startswith("multipart/form-data")
            ):
                logger.warning(
                    f"Invalid content type for auth endpoint: {content_type}"
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid content type",
                )

    def _check_attack_patterns(self, request: Request):
        """Check for common attack patterns in request headers."""

        attack_patterns = [
            # SQL injection patterns
            "union select",
            "drop table",
            "insert into",
            "delete from",
            # XSS patterns
            "<script",
            "javascript:",
            "onerror=",
            "onload=",
            # Path traversal
            "../",
            "..\\",
            "..\\/",
            # Command injection
            "; cat ",
            "| nc ",
            "&& curl",
        ]

        # Check all headers
        for header_name, header_value in request.headers.items():
            header_value_lower = header_value.lower()
            for pattern in attack_patterns:
                if pattern in header_value_lower:
                    client_ip = self._get_client_ip(request)
                    logger.warning(
                        f"Attack pattern detected in header {header_name} "
                        f"from {client_ip}: {pattern}"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid request",
                    )

    def _add_auth_security_headers(self, response: Response):
        """Add additional security headers for auth endpoints."""

        # Add auth-specific security headers
        response.headers.update(
            {
                # Prevent caching of auth responses
                "Cache-Control": "no-store, no-cache, must-revalidate, private",
                "Pragma": "no-cache",
                "Expires": "0",
                # Additional security headers
                "X-Permitted-Cross-Domain-Policies": "none",
                "Cross-Origin-Embedder-Policy": "require-corp",
                "Cross-Origin-Opener-Policy": "same-origin",
                "Cross-Origin-Resource-Policy": "same-origin",
                # Prevent MIME sniffing
                "X-Content-Type-Options": "nosniff",
                # Enforce HTTPS (if not already set)
                "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
            }
        )

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


class ContentSecurityPolicyMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add Content Security Policy headers.

    This helps prevent XSS attacks by controlling what resources
    the browser is allowed to load.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add CSP headers to response."""

        response = await call_next(request)

        # Only add CSP for HTML responses
        content_type = response.headers.get("content-type", "")
        if "text/html" in content_type:
            # Check if this is a Swagger UI docs page
            if request.url.path in ["/docs", "/redoc"]:
                # More permissive CSP for Swagger UI/ReDoc
                csp_policy = (
                    "default-src 'self'; "
                    "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
                    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                    "img-src 'self' data: https:; "
                    "font-src 'self' https://cdn.jsdelivr.net; "
                    "connect-src 'self'; "
                    "frame-ancestors 'none'; "
                    "base-uri 'self'; "
                    "form-action 'self'"
                )
            else:
                # Standard CSP for other pages
                csp_policy = (
                    "default-src 'self'; "
                    "script-src 'self' 'unsafe-inline'; "
                    "style-src 'self' 'unsafe-inline'; "
                    "img-src 'self' data: https:; "
                    "font-src 'self'; "
                    "connect-src 'self'; "
                    "frame-ancestors 'none'; "
                    "base-uri 'self'; "
                    "form-action 'self'"
                )

            response.headers["Content-Security-Policy"] = csp_policy

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Enhanced request logging middleware for security monitoring.

    Logs detailed information about requests for security analysis.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request details for security monitoring."""

        start_time = time.time()
        client_ip = self._get_client_ip(request)

        # Log request details
        logger.info(
            f"Request: {request.method} {request.url.path} "
            f"from {client_ip} "
            f"User-Agent: {request.headers.get('user-agent', 'Unknown')}"
        )

        try:
            response = await call_next(request)

            # Log response details
            process_time = time.time() - start_time
            logger.info(
                f"Response: {response.status_code} "
                f"Time: {process_time:.3f}s "
                f"Size: {response.headers.get('content-length', 'Unknown')}"
            )

            # Log security events
            if response.status_code >= 400:
                logger.warning(
                    f"HTTP {response.status_code} response for "
                    f"{request.method} {request.url.path} from {client_ip}"
                )

            return response

        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"Request failed: {request.method} {request.url.path} "
                f"from {client_ip} "
                f"Error: {e!s} "
                f"Time: {process_time:.3f}s",
                exc_info=True,
            )
            raise

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        return request.client.host if request.client else "unknown"
