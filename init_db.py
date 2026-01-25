#!/usr/bin/env python3
"""
Database initialization script.

This script creates the necessary database tables for the application.
Uses environment variables from .env file for credentials.
NO credentials are hardcoded.
"""

import os
import sys
import logging
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Load environment variables from .env
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_database_url() -> str:
    """
    Construct database URL from environment variables.
    All credentials come from .env file only.
    """
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "3306")
    db_user = os.getenv("DB_USER", "root")
    db_password = os.getenv("DB_PASSWORD", "")
    db_name = os.getenv("DB_NAME", "uddhava_db")

    if not db_password:
        raise ValueError("DB_PASSWORD environment variable is required")

    # URL encode the password to handle special characters
    from urllib.parse import quote_plus
    encoded_password = quote_plus(db_password)

    database_url = (
        f"mysql+pymysql://{db_user}:{encoded_password}"
        f"@{db_host}:{db_port}/{db_name}"
    )
    return database_url


def create_database_tables():
    """Create database tables using SQLAlchemy models."""
    try:
        database_url = get_database_url()
        logger.info(f"Connecting to database at {database_url.split('@')[1]}")

        engine = create_engine(database_url)

        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            logger.info("✓ Database connection successful")

        # Import models
        from app.db.models import Base
        logger.info("Creating tables from models...")

        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("✓ All tables created successfully")

        # List created tables
        with engine.connect() as conn:
            result = conn.execute(text("SHOW TABLES"))
            tables = [row[0] for row in result.fetchall()]
            logger.info(f"Tables in database: {', '.join(tables)}")

        return True

    except SQLAlchemyError as e:
        logger.error(f"✗ Database error: {e}")
        return False
    except ValueError as e:
        logger.error(f"✗ Configuration error: {e}")
        return False
    except Exception as e:
        logger.error(f"✗ Unexpected error: {e}")
        return False


def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("Database Initialization Script")
    logger.info("=" * 60)

    # Check if .env exists
    if not Path(".env").exists():
        logger.error("✗ .env file not found. Please create it from .env.example")
        sys.exit(1)

    logger.info("Reading configuration from .env...")

    # Create tables
    if create_database_tables():
        logger.info("=" * 60)
        logger.info("✓ Database initialization completed successfully!")
        logger.info("=" * 60)
        sys.exit(0)
    else:
        logger.error("=" * 60)
        logger.error("✗ Database initialization failed")
        logger.error("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
