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

from app.core.auth_decorators import admin_only_endpoint
from app.core.config import settings
from app.core.monitoring import get_comprehensive_metrics
from app.core.security import get_current_user
from app.db.models import Devotee
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
@admin_only_endpoint
def get_metrics(current_user: Devotee = Depends(get_current_user)):
    """
    Get comprehensive application metrics for monitoring.

    Returns detailed metrics including:
    - Application health status
    - Performance metrics
    - Request statistics
    - System resource usage

    This endpoint is typically used by monitoring systems
    like Prometheus, Grafana, or custom dashboards.

    **Access Control:**
    - Admin users only
    - Contains sensitive system information
    """
    return get_comprehensive_metrics()


# Debug endpoint (conditionally available)
if not settings.is_production:

    @router.get("/debug/db", summary="Database Debug Information")
    @admin_only_endpoint
    def debug_database_info(
        current_user: Devotee = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        """
        Get database debug information.

        Returns comprehensive database statistics and health information:
        - Connection pool status
        - Table counts and sizes
        - Index information
        - Performance metrics

        Useful for troubleshooting database-related issues.

        **Access Control:**
        - Admin users only
        - Contains sensitive database structure and statistics
        """
        try:
            # Get table information
            tables_info = []

            # Use text() for raw SQL to avoid SQLAlchemy warnings
            result = db.execute(
                text(
                    """
                SELECT
                    table_name,
                    COALESCE(n_tup_ins, 0) as inserts,
                    COALESCE(n_tup_upd, 0) as updates,
                    COALESCE(n_tup_del, 0) as deletes,
                    COALESCE(n_live_tup, 0) as live_tuples,
                    COALESCE(n_dead_tup, 0) as dead_tuples
                FROM pg_stat_user_tables
                WHERE schemaname = 'public'
                ORDER BY table_name
            """
                )
            )

            for row in result:
                tables_info.append(
                    {
                        "table_name": row.table_name,
                        "inserts": row.inserts,
                        "updates": row.updates,
                        "deletes": row.deletes,
                        "live_tuples": row.live_tuples,
                        "dead_tuples": row.dead_tuples,
                    }
                )

            return {
                "status": "success",
                "database_info": {
                    "tables": tables_info,
                    "connection_status": "healthy",
                },
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {e!s}",
            ) from e
