"""
Application middleware for error handling, logging, and request processing.

This module contains custom middleware classes for handling various
aspects of request/response processing in production environments.
"""

import logging
import time
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all requests and responses with timing information.

    This middleware logs details about every request including:
    - Request method and path
    - Response status code
    - Processing time
    - Client IP address
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details."""
        start_time = time.time()

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Log request
        logger.info(f"Request started: {request.method} {request.url.path} from {client_ip}")

        try:
            # Process request
            response = await call_next(request)

            # Calculate processing time
            process_time = time.time() - start_time

            # Log response
            logger.info(
                f"Request completed: {request.method} {request.url.path} "
                f"- Status: {response.status_code} "
                f"- Time: {process_time:.3f}s"
            )

            # Add timing header
            response.headers["X-Process-Time"] = str(process_time)

            return response

        except Exception as e:
            # Log error
            process_time = time.time() - start_time
            logger.error(
                f"Request failed: {request.method} {request.url.path} "
                f"- Error: {str(e)} "
                f"- Time: {process_time:.3f}s",
                exc_info=True,
            )
            raise


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.

    This middleware adds common security headers to improve
    the security posture of the application.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response."""
        response = await call_next(request)

        # Add security headers
        response.headers.update(
            {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "X-XSS-Protection": "1; mode=block",
                "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
                "Referrer-Policy": "strict-origin-when-cross-origin",
            }
        )

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple rate limiting middleware.

    This is a basic implementation for demonstration.
    In production, consider using Redis-based rate limiting.
    """

    def __init__(self, app, calls: int = 100, period: int = 60):
        """
        Initialize rate limiter.

        Args:
            app: FastAPI application
            calls: Number of calls allowed per period
            period: Time period in seconds
        """
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.clients = {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply rate limiting."""
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()

        # Clean old entries
        self.clients = {
            ip: timestamps
            for ip, timestamps in self.clients.items()
            if any(ts > current_time - self.period for ts in timestamps)
        }

        # Get client's request history
        if client_ip not in self.clients:
            self.clients[client_ip] = []

        # Filter recent requests
        self.clients[client_ip] = [
            ts for ts in self.clients[client_ip] if ts > current_time - self.period
        ]

        # Check rate limit
        if len(self.clients[client_ip]) >= self.calls:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            from fastapi import HTTPException

            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        # Record this request
        self.clients[client_ip].append(current_time)

        return await call_next(request)


# Custom exception classes
class ApplicationError(Exception):
    """Base exception class for application errors."""

    def __init__(self, message: str, error_code: str = None):
        self.message = message
        self.error_code = error_code
        super().__init__(message)


class ValidationError(ApplicationError):
    """Exception for validation errors."""

    pass


class AuthenticationError(ApplicationError):
    """Exception for authentication errors."""

    pass


class AuthorizationError(ApplicationError):
    """Exception for authorization errors."""

    pass


class DatabaseError(ApplicationError):
    """Exception for database errors."""

    pass


class FileUploadError(ApplicationError):
    """Exception for file upload errors."""

    pass
