"""
Main FastAPI application entry point.

This module creates and configures the FastAPI application with proper
middleware, exception handlers, and route registration following production
best practices.
"""

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes import (
    auth,
    health,
)
from app.core.auth_middleware import (
    AuthSecurityMiddleware,
    ContentSecurityPolicyMiddleware,
    RequestLoggingMiddleware,
)
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.middleware import (
    LoggingMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
)
from app.core.openapi import get_custom_openapi
from app.db.models import Base
from app.db.session import engine

# Configure logging
setup_logging()
logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """
    FastAPI lifespan context manager.

    Handles application startup and shutdown events with graceful database handling.
    """
    # Startup
    logger.info("Starting up application...")

    # Try to initialize database tables with fallback handling
    if not settings.is_production and os.getenv("SKIP_DB_INIT") != "1":
        try:
            logger.info("Attempting to create database tables in development mode")
            # Test database connection first
            with engine.connect() as conn:
                from sqlalchemy import text

                conn.execute(text("SELECT 1"))
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.warning(f"Database initialization failed: {e}")
            logger.info("Application will start without database connectivity")
            logger.info("Database-dependent endpoints will return appropriate errors")

    # Log application configuration
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")

    # Log database URL safely
    try:
        db_url_str = str(settings.get_database_url())
        db_info = db_url_str.split("@")[-1] if "@" in db_url_str else "localhost"
        logger.info(f"Database URL: {db_info}")
    except Exception:
        logger.info("Database configuration loaded")

    yield

    # Shutdown
    logger.info("Shutting down application...")


def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        FastAPI: Configured FastAPI application instance
    """
    app = FastAPI(
        title="Radha Shyam Sundar Yatra - Uddhava API Endpoints",
        version=settings.app_version,
        description=(
            "An application dedicated to managing and supporting the Radha Shyam Sundar Yatra."
        ),
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # Configure middleware
    setup_middleware(app)

    # Configure exception handlers
    setup_exception_handlers(app)

    # Register routes
    register_routes(app)

    # Apply custom OpenAPI schema for enhanced Swagger UI documentation
    # Note: This creates a custom method, not assigning to existing one
    app.openapi = lambda: get_custom_openapi(app)  # type: ignore[method-assign]

    return app


def setup_middleware(app: FastAPI) -> None:
    """Configure application middleware."""

    # CORS middleware - MUST be added first so it handles preflight OPTIONS requests
    # before other middleware can reject them
    # Note: Cannot use "*" with allow_credentials=True (CORS specification)
    # Instead, explicitly list allowed origins
    allowed_origins: list = [
        "https://rsyatra.com",  # Production frontend (custom domain)
        "https://www.rsyatra.com",  # Production frontend with www (custom domain)
        "https://rsyatra.onrender.com",  # Production frontend (Render subdomain - legacy)
        "https://dev-rsyatra.onrender.com",  # Development frontend (Render subdomain)
        "http://localhost:5173",  # Local frontend for development
        "http://localhost:5174",  # Local frontend for development (when 5173 is in use)
        "http://localhost:8000",  # Backend testing
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
        expose_headers=["*"],  # Allow frontend to read all response headers
        max_age=3600,  # Cache preflight requests for 1 hour
    )

    # Custom middleware (order matters - added first, executed last)
    if not settings.is_production:
        # Rate limiting in development for testing
        app.add_middleware(RateLimitMiddleware, calls=1000, period=60)

    # Auth-specific security middleware
    app.add_middleware(AuthSecurityMiddleware)

    # Content Security Policy middleware
    app.add_middleware(ContentSecurityPolicyMiddleware)

    # Enhanced request logging middleware
    app.add_middleware(RequestLoggingMiddleware)

    # Security headers
    app.add_middleware(SecurityHeadersMiddleware)

    # Request logging
    app.add_middleware(LoggingMiddleware)

    # Trusted host middleware for production
    if settings.is_production:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=[
                "localhost",
                "127.0.0.1",
                "*.run.app",
                "rsyatra.com",
                "*.rsyatra.com",
                "*.onrender.com",
                "http://localhost:5173"
            ]
            + ([settings.app_host] if hasattr(settings, "app_host") else []),
        )


def setup_exception_handlers(app: FastAPI) -> None:
    """Configure application exception handlers."""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """
        Handle HTTP exceptions with standardized response format.

        Converts all HTTPException instances (including StandardHTTPException)
        to the standard API response format for consistency.
        """
        logger.warning(
            f"HTTP {exc.status_code} error on {request.method} {request.url.path}: {exc.detail}"
        )

        # Check if this is our custom StandardHTTPException with additional fields
        from app.core.responses import StandardHTTPException

        if isinstance(exc, StandardHTTPException):
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "success": exc.success,
                    "status_code": exc.status_code,
                    "message": exc.message,
                    "data": exc.data,
                },
            )

        # For regular HTTPException, convert to standard format
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "status_code": exc.status_code,
                "message": exc.detail,
                "data": None,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle request validation errors with standardized response format."""
        logger.warning(f"Request validation error on {request.method} {request.url.path}: {exc}")

        # Extract user-friendly error message from first error
        errors = exc.errors()
        if errors:
            first_error = errors[0]

            # Get the error message
            if "ctx" in first_error and "error" in first_error["ctx"]:
                error_msg = str(first_error["ctx"]["error"])
            else:
                error_msg = first_error.get("msg", "Validation failed")

            # Create a clean, user-friendly message
            if len(errors) > 1:
                message = f"{error_msg} (and {len(errors) - 1} more validation error{'s' if len(errors) > 1 else ''})"
            else:
                message = error_msg
        else:
            message = "Request validation failed"

        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "status_code": 422,
                "message": message,
                "data": None,
            },
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_exception_handler(request: Request, exc: SQLAlchemyError):
        """
        Handle database errors with standardized response format.

        Logs detailed error information for debugging while returning
        a user-friendly error message to the client.
        """
        # Log detailed error information for debugging
        logger.error(
            f"Database error on {request.method} {request.url.path}: {exc}",
            exc_info=True,
            extra={"error_type": type(exc).__name__, "error_details": str(exc)},
        )
        # Also print to stdout for Cloud Run logs
        print(f"DATABASE ERROR: {type(exc).__name__}: {exc}", flush=True)

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "status_code": 500,
                "message": "Internal server error",
                "data": None,
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """
        Handle unexpected errors with standardized response format.

        Catches all unhandled exceptions and returns a safe error message
        to the client while logging detailed information for debugging.
        """
        logger.error(
            f"Unexpected error on {request.method} {request.url.path}: {exc}",
            exc_info=True,
        )

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "status_code": 500,
                "message": "Internal server error",
                "data": None,
            },
        )


def register_routes(app: FastAPI) -> None:
    """Register application routes."""

    # Health checks (no authentication required)
    app.include_router(health.router, prefix="/api/v1")

    # Authentication routes
    app.include_router(auth.router, prefix="/api/v1")

    # Root endpoint - Landing page
    @app.get("/", tags=["Root"], include_in_schema=False)
    async def root(request: Request):
        """
        Landing page with API information and navigation.

        Serves as the main entry point for the Uddhava API,
        providing navigation and basic service information.
        """
        import os

        from fastapi.templating import Jinja2Templates

        # Setup templates
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        templates = Jinja2Templates(directory=template_dir)

        # Render template with context
        template_context = {
            "request": request,
            "app_name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment.title(),
            "description": "RSYatra Authentication API",
            "show_docs": not settings.is_production,
        }

        return templates.TemplateResponse("index.html", template_context)

    # API info endpoint (JSON format for programmatic access)
    @app.get("/api/info", tags=["Root"])
    async def api_info():
        """Get API information in JSON format for programmatic access."""
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "status": "running",
            "description": "RSYatra Authentication API",
            "endpoints": {
                "health": "/api/v1/health",
                "auth": "/api/v1/auth",
                "docs": "/docs" if not settings.is_production else None,
                "redoc": "/redoc" if not settings.is_production else None,
            },
        }


# Create the application instance
app = create_application()


# Development server entry point
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",  # nosec: B104 - Intentional for containerized deployment
        port=int(os.getenv("PORT", "8000")),
        reload=not settings.is_production,
        log_level="info" if settings.is_production else "debug",
    )
