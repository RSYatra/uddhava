"""
Health check and system monitoring endpoints.

This module contains health check endpoints for monitoring the application
status, database connectivity, and system information.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.db.session import SessionLocal, engine
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
            timestamp=datetime.now(datetime.timezone.utc),
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
