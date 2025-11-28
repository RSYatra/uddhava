"""
Health check and system monitoring endpoints.

This module contains health check endpoints for monitoring the application
status, database connectivity, and system information.
"""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.responses import StandardHTTPException
from app.db.session import check_database_health, engine
from app.schemas.health import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse, summary="Health Check")
def health_check():
    """
    Check the health status of the application.

    This endpoint checks:
    - API server status
    - Database connectivity
    - Basic system information

    Returns health status information.
    """
    try:
        # Test database connectivity
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        return HealthResponse(
            status="healthy",
            timestamp=datetime.now(UTC),
            version=settings.app_version,
        )

    except SQLAlchemyError:
        logger.exception("Database health check failed")
        raise StandardHTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message="Database connection failed",
            success=False,
            data=None,
        ) from None
    except Exception:
        logger.exception("Health check failed")
        raise StandardHTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message="Health check failed",
            success=False,
            data=None,
        ) from None


@router.get("/health/database", summary="Database Health Check")
def database_health_check():
    """
    Detailed database health check endpoint.

    Returns comprehensive database health information including:
    - Connection status
    - Connection pool statistics
    - Response time
    - Error details (if any)

    This is useful for monitoring and debugging database connectivity issues.
    """
    db_health = check_database_health()

    if db_health["status"] == "healthy":
        return {
            "success": True,
            "status_code": 200,
            "message": "Database is healthy",
            "data": db_health,
        }
    else:
        logger.error(f"Database health check failed: {db_health.get('error')}")
        raise StandardHTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message=f"Database is unhealthy: {db_health.get('error')}",
            success=False,
            data=None,
        )
