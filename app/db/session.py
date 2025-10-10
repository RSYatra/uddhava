"""
Database configuration and session management.

This module sets up SQLAlchemy engine, session factory, and provides
database connection utilities with production-grade reliability features.
"""

import logging
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from app.core.config import settings

logger = logging.getLogger("app.db")


engine = create_engine(
    settings.database_url,
    # Connection pool settings
    poolclass=QueuePool,
    pool_size=10,  # Base number of connections
    max_overflow=20,  # Additional connections when needed
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=3600,  # Recycle connections every hour
    pool_timeout=30,  # Timeout for getting connection from pool
    # Query and execution settings
    echo=settings.debug,  # Log SQL in debug mode
    echo_pool=settings.debug,  # Log pool events in debug mode
    future=True,  # Use SQLAlchemy 2.0 style
    # Connection arguments for MySQL optimization
    connect_args=(
        {
            "charset": "utf8mb4",
            "autocommit": False,
            "connect_timeout": 60,
            "read_timeout": 30,
            "write_timeout": 30,
        }
        if "mysql" in settings.database_url
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


# Event listeners for connection monitoring
@event.listens_for(engine, "connect")
def connect_handler(dbapi_connection, connection_record):
    """Log successful database connections."""
    logger.debug("New database connection established")


@event.listens_for(engine, "checkout")
def checkout_handler(dbapi_connection, connection_record, connection_proxy):
    """Log connection checkout from pool."""
    logger.debug("Connection checked out from pool")


@event.listens_for(engine, "checkin")
def checkin_handler(dbapi_connection, connection_record):
    """Log connection return to pool."""
    logger.debug("Connection returned to pool")


# Database dependency
def get_db() -> Generator[Session]:
    """
    Database dependency that provides a database session.

    Yields:
        SQLAlchemy database session with automatic cleanup

    Note:
        Connection pooling and retry logic is handled by the SQLAlchemy engine
        configuration (pool_pre_ping, pool_recycle, etc).
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


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
