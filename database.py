import logging
import os
from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

# Load environment variables from .env file (for local development)
try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
except ImportError:  # pragma: no cover - optional dependency
    pass

# Direct environment-based configuration (credentials.py removed)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")  # nosec B105 - local dev default
DB_NAME = os.getenv("DB_NAME", "uddhava_db")

# Validate required configuration
if not all([DB_HOST, DB_USER, DB_NAME]) or DB_PASSWORD is None:
    raise ValueError("Missing required database configuration")

# Additional validation for production safety
if not DB_HOST or not DB_USER or not DB_NAME:
    raise ValueError("Database configuration values cannot be empty")

# URL encode the password to handle special characters
encoded_password = quote_plus(str(DB_PASSWORD))

DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{encoded_password}@" f"{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# Database engine with production settings
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=3600,  # Recycle connections every hour
    pool_size=10,  # Connection pool size
    max_overflow=20,  # Maximum overflow connections
    echo=os.getenv("SQL_DEBUG", "").lower() == "true",  # Log SQL in debug mode
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

logger.info(f"Database configured: {DB_HOST}:{DB_PORT}/{DB_NAME}")
