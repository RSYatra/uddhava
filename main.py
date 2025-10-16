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
from starlette.middleware.sessions import SessionMiddleware

from app.api.routes import devotee_auth, devotees, health
from app.core.auth_middleware import (
    AuthSecurityMiddleware,
    ContentSecurityPolicyMiddleware,
    RequestLoggingMiddleware,
)
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.middleware import (
    ApplicationError,
    AuthenticationError,
    AuthorizationError,
    FileUploadError,
    LoggingMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    ValidationError,
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
        db_url_str = str(settings.database_url)
        db_info = db_url_str.split("@")[-1] if "@" in db_url_str else "localhost"
        logger.info(f"Database URL: {db_info}")
    except Exception:
        logger.info("Database configuration loaded")

    # Check for admin user existence
    try:
        from app.utils.admin_utils import ensure_admin_exists

        if ensure_admin_exists():
            logger.info("Admin user verification completed")
        else:
            logger.warning(
                "No admin users found. Create one using: "
                "promote_user_to_admin() or create_admin_user()"
            )
    except Exception as e:
        logger.warning(f"Admin user check failed: {e}")

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
    app.openapi = lambda: get_custom_openapi(app)

    return app


def setup_middleware(app: FastAPI) -> None:
    """Configure application middleware."""

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

    # CORS middleware
    # Note: Cannot use "*" with allow_credentials=True (CORS specification)
    # Instead, explicitly list allowed origins
    allowed_origins = [
        "https://rsyatra.onrender.com",  # Production frontend
        "http://localhost:1728",  # Local frontend for development
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

    # Trusted host middleware for production
    if settings.is_production:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["localhost", "127.0.0.1"]
            + ([settings.app_host] if hasattr(settings, "app_host") else []),
        )

    # Session middleware for authentication
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.jwt_secret_key,
        max_age=86400,  # 24 hours
        same_site="lax",
        https_only=settings.is_production,
    )


def setup_exception_handlers(app: FastAPI) -> None:
    """Configure application exception handlers."""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions with proper logging."""
        logger.warning(
            f"HTTP {exc.status_code} error on {request.method} {request.url.path}: {exc.detail}"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "status_code": exc.status_code},
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
        """Handle database errors."""
        logger.error(f"Database error on {request.method} {request.url.path}: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "error_type": "database_error",
                "status_code": 500,
            },
        )

    @app.exception_handler(ApplicationError)
    async def application_exception_handler(request: Request, exc: ApplicationError):
        """Handle custom application errors."""
        logger.warning(f"Application error on {request.method} {request.url.path}: {exc.message}")
        return JSONResponse(
            status_code=400,
            content={
                "detail": exc.message,
                "error_code": exc.error_code,
                "status_code": 400,
            },
        )

    @app.exception_handler(AuthenticationError)
    async def authentication_exception_handler(request: Request, exc: AuthenticationError):
        """Handle authentication errors."""
        logger.warning(
            f"Authentication error on {request.method} {request.url.path}: {exc.message}"
        )
        return JSONResponse(
            status_code=401,
            content={
                "detail": exc.message,
                "error_code": exc.error_code,
                "status_code": 401,
            },
        )

    @app.exception_handler(AuthorizationError)
    async def authorization_exception_handler(request: Request, exc: AuthorizationError):
        """Handle authorization errors."""
        logger.warning(f"Authorization error on {request.method} {request.url.path}: {exc.message}")
        return JSONResponse(
            status_code=403,
            content={
                "detail": exc.message,
                "error_code": exc.error_code,
                "status_code": 403,
            },
        )

    @app.exception_handler(ValidationError)
    async def validation_exception_handler(request: Request, exc: ValidationError):
        """Handle custom validation errors."""
        logger.warning(f"Validation error on {request.method} {request.url.path}: {exc.message}")
        return JSONResponse(
            status_code=422,
            content={
                "detail": exc.message,
                "error_code": exc.error_code,
                "status_code": 422,
            },
        )

    @app.exception_handler(FileUploadError)
    async def file_upload_exception_handler(request: Request, exc: FileUploadError):
        """Handle file upload errors."""
        logger.warning(f"File upload error on {request.method} {request.url.path}: {exc.message}")
        return JSONResponse(
            status_code=400,
            content={
                "detail": exc.message,
                "error_code": exc.error_code,
                "status_code": 400,
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected errors."""
        logger.error(
            f"Unexpected error on {request.method} {request.url.path}: {exc}",
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "error_type": "unexpected_error",
                "status_code": 500,
            },
        )


def register_routes(app: FastAPI) -> None:
    """Register application routes."""

    # Health checks (no authentication required)
    app.include_router(health.router, prefix="/api/v1")

    # Devotee authentication routes (new unified auth system)
    app.include_router(devotee_auth.router, prefix="/api/v1")

    # Devotee routes (enhanced user management)
    app.include_router(devotees.router, prefix="/api/v1")

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
            "description": "Radha Shyam Sundar Yatra Management System",
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
            "description": "Radha Shyam Sundar Yatra Management API",
            "endpoints": {
                "health": "/api/v1/health",
                "devotees": "/api/v1/devotees/",  # Enhanced devotee management
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
