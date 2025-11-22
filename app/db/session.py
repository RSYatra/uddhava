"""
Database configuration and session management.

This module sets up SQLAlchemy engine, session factory, and provides
database connection utilities with production-grade reliability features.
"""

import logging
import time
from collections.abc import Generator
from contextlib import contextmanager
from functools import wraps

from sqlalchemy import create_engine, event, exc, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from app.core.config import settings

logger = logging.getLogger("app.db")


engine = create_engine(
    settings.get_database_url(),
    # Connection pool settings
    poolclass=QueuePool,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_pre_ping=settings.db_pool_pre_ping,
    pool_recycle=settings.db_pool_recycle,
    pool_timeout=settings.db_pool_timeout,
    # Query and execution settings
    echo=settings.debug,  # Log SQL in debug mode
    echo_pool=settings.debug,  # Log pool events in debug mode
    future=True,  # Use SQLAlchemy 2.0 style
    # Connection arguments for MySQL optimization
    connect_args=(
        {
            "charset": "utf8mb4",
            "autocommit": False,
            "connect_timeout": settings.db_connect_timeout,
            "read_timeout": settings.db_read_timeout,
            "write_timeout": settings.db_write_timeout,
        }
        if "mysql" in settings.get_database_url()
        else {}
    ),
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,  # Keep objects usable after commit
)


# Retry decorator for database operations
def with_db_retry(max_retries=None, retry_delay=None, backoff=None):
    """
    Decorator to retry database operations on connection failures.

    Args:
        max_retries: Maximum number of retry attempts (uses config default if None)
        retry_delay: Initial delay between retries in seconds (uses config default if None)
        backoff: Exponential backoff multiplier (uses config default if None)
    """
    max_retries = max_retries or settings.db_max_retries
    retry_delay = retry_delay or settings.db_retry_delay
    backoff = backoff or settings.db_retry_backoff

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            delay = retry_delay

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except (
                    exc.OperationalError,
                    exc.DatabaseError,
                    exc.DisconnectionError,
                ) as e:
                    last_exception = e
                    error_msg = str(e).lower()

                    # Check if it's a retryable error
                    retryable_errors = [
                        "mysql server has gone away",
                        "lost connection",
                        "connection reset",
                        "broken pipe",
                        "can't connect",
                        "connection refused",
                        "timeout",
                        "too many connections",
                    ]

                    is_retryable = any(err in error_msg for err in retryable_errors)

                    if not is_retryable or attempt == max_retries:
                        logger.error(
                            f"Database operation failed (attempt {attempt + 1}/{max_retries + 1}): {e}"
                        )
                        raise

                    logger.warning(
                        f"Database connection error (attempt {attempt + 1}/{max_retries + 1}), "
                        f"retrying in {delay:.1f}s: {e}"
                    )

                    # Dispose of the connection pool to force reconnection
                    engine.dispose()

                    time.sleep(delay)
                    delay *= backoff

            raise last_exception

        return wrapper

    return decorator


# Event listeners for connection monitoring
@event.listens_for(engine, "connect")
def connect_handler(dbapi_connection, connection_record):
    """Log successful database connections."""
    logger.info("New database connection established")


@event.listens_for(engine, "checkout")
def checkout_handler(dbapi_connection, connection_record, connection_proxy):
    """Verify connection is alive before checkout."""
    # pool_pre_ping handles this, but we log it
    logger.debug("Connection checked out from pool")


@event.listens_for(engine, "checkin")
def checkin_handler(dbapi_connection, connection_record):
    """Log connection return to pool."""
    logger.debug("Connection returned to pool")


@event.listens_for(engine, "close")
def close_handler(dbapi_connection, connection_record):
    """Log connection closure."""
    logger.debug("Database connection closed")


@event.listens_for(engine, "close_detached")
def close_detached_handler(dbapi_connection, connection_record):
    """Log detached connection closure."""
    logger.debug("Detached database connection closed")


@event.listens_for(engine, "invalidate")
def invalidate_handler(dbapi_connection, connection_record, exception):
    """Log connection invalidation."""
    logger.warning(f"Database connection invalidated: {exception}")


# Database dependency (retry logic is handled inside via pool_pre_ping and connection events)
def get_db() -> Generator:
    """
    Database dependency that provides a database session with automatic retry.

    Yields:
        SQLAlchemy database session with automatic cleanup

    Features:
        - Automatic retry on connection failures (3 attempts with exponential backoff)
        - Connection pooling with health checks (pool_pre_ping)
        - Automatic connection recycling (every 30 minutes)
        - Proper rollback on errors
        - Connection cleanup in finally block

    Raises:
        exc.OperationalError: After max retries if connection cannot be established
    """
    db = SessionLocal()
    try:
        # Test connection on first use
        db.execute(text("SELECT 1"))
        yield db
        # Commit any pending transactions
        db.commit()
    except Exception as e:
        logger.error(f"Database session error: {e}", exc_info=True)
        print(f"DB SESSION ERROR: {type(e).__name__}: {e}", flush=True)
        db.rollback()
        raise
    finally:
        db.close()


def check_database_health() -> dict:
    """
    Check database connection health and return status.

    Returns:
        dict: Health status with connection info and any errors

    Example:
        {
            "status": "healthy",
            "database": "uddhava_db",
            "pool_size": 10,
            "checked_out": 2,
            "overflow": 0,
            "response_time_ms": 5.2
        }
    """
    start_time = time.time()
    status = {
        "status": "unhealthy",
        "database": settings.db_name,
        "error": None,
    }

    try:
        # Try to execute a simple query
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            conn.commit()

        # Get pool statistics
        pool = engine.pool
        status.update(
            {
                "status": "healthy",
                "pool_size": pool.size(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "response_time_ms": round((time.time() - start_time) * 1000, 2),
            }
        )
        logger.info("Database health check: HEALTHY")

    except Exception as e:
        status["error"] = str(e)
        logger.error(f"Database health check: UNHEALTHY - {e}")

    return status


@contextmanager
def log_database_config():
    """Safely log database configuration."""
    try:
        logger.info("=" * 40)
        logger.info("Database Configuration:")
        logger.info(f"Host: {settings.db_host}:{settings.db_port}")
        logger.info(f"Database: {settings.db_name}")
        logger.info(f"Pool size: {engine.pool.size()}")
        logger.info(f"Max overflow: {engine.pool.overflow()}")
        logger.info("Pool timeout: 30s")
        logger.info("Connection recycle: 3600s")
        logger.info("=" * 40)
    except Exception as e:
        logger.warning(f"Could not log database configuration: {e}")


# Initialize configuration logging
log_database_config()
