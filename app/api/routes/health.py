"""
Health check and system monitoring endpoints.

This module contains health check endpoints for monitoring the application
status, database connectivity, and system information.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.monitoring import get_comprehensive_metrics
from app.db.session import SessionLocal, engine
from app.schemas.user import HealthResponse

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
def health_check(db: Session = Depends(get_db)):
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
            timestamp=datetime.utcnow(),
            version=settings.app_version,
        )

    except SQLAlchemyError:
        logger.exception("Database health check failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed",
        )
    except Exception:
        logger.exception("Health check failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Health check failed",
        )


@router.get("/health/ready", summary="Readiness Check")
def readiness_check(db: Session = Depends(get_db)):
    """
    Check if the application is ready to serve requests.

    This is typically used by orchestrators like Kubernetes
    to determine if the application is ready for traffic.
    """
    try:
        # Test database connectivity
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        return {"status": "ready", "timestamp": datetime.utcnow()}

    except SQLAlchemyError:
        logger.exception("Readiness check failed - database issue")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready - database unavailable",
        )


@router.get("/health/live", summary="Liveness Check")
def liveness_check():
    """
    Check if the application is alive and responding.

    This is typically used by orchestrators like Kubernetes
    to determine if the application should be restarted.
    """
    return {"status": "alive", "timestamp": datetime.utcnow()}


@router.get("/metrics", summary="Application Metrics")
def get_metrics():
    """
    Get comprehensive application metrics for monitoring.

    Returns detailed metrics including:
    - Application health status
    - Performance metrics
    - Request statistics
    - System resource usage

    This endpoint is typically used by monitoring systems
    like Prometheus, Grafana, or custom dashboards.
    """
    return get_comprehensive_metrics()


# Debug endpoint (conditionally available)
if not settings.is_production:

    @router.get("/debug/db", summary="Database Debug Info")
    def debug_database_info(db: Session = Depends(get_db)):
        """
        Get database connection and configuration information.

        This endpoint is only available in non-production environments
        for debugging purposes.
        """
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT VERSION() as version"))
                db_version = result.fetchone()

                return {
                    "database_url": (
                        str(settings.database_url).replace(settings.db_password, "***")
                        if settings.db_password
                        else str(settings.database_url)
                    ),
                    "database_version": (
                        dict(db_version._mapping) if db_version else None
                    ),
                    "engine_info": {
                        "name": engine.name,
                        "driver": engine.driver,
                        "pool_class": str(type(engine.pool).__name__),
                    },
                }
        except SQLAlchemyError as e:
            logger.exception("Database debug info failed")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(e)}",
            )
