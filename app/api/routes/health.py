"""
Health check and system monitoring endpoints.

This module contains health check endpoints for monitoring the application
status, database connectivity, and system information.
"""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.db.session import SessionLocal, check_database_health, engine
from app.schemas.health import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


def get_db():
    """Database dependency for health checks."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        logger.exception("Database error during health check")
    finally:
        db.close()


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
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed",
        ) from None
    except Exception:
        logger.exception("Health check failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Health check failed",
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
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database is unhealthy: {db_health.get('error')}",
        )
