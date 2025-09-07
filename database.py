import logging
import os
from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

# Load environment variables from .env file (for local development)
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # dotenv not installed, skip loading .env file

# Try to import credentials as fallback for local development
try:
    import credentials

    default_host = credentials.DB_HOST
    default_port = credentials.DB_PORT
    default_user = credentials.DB_USER
    default_password = credentials.DB_PASSWORD
    default_name = getattr(credentials, "DB_NAME", "uddhava_db")
    logger.info("Using credentials.py for database configuration")
except ImportError:
    # Fallback defaults when credentials.py doesn't exist (production)
    default_host = "localhost"
    default_port = 3306
    default_user = "root"
    default_password = ""  # nosec B105 - Empty password for local dev only
    default_name = "uddhava_db"
    logger.info("Using environment variables for database configuration")

# Environment variables take priority over credentials.py
DB_HOST = os.getenv("DB_HOST", default_host)
DB_PORT = int(os.getenv("DB_PORT", str(default_port)))
DB_USER = os.getenv("DB_USER", default_user)
DB_PASSWORD = os.getenv("DB_PASSWORD", default_password)
DB_NAME = os.getenv("DB_NAME", default_name)

# Validate required configuration
if not all([DB_HOST, DB_USER, DB_PASSWORD, DB_NAME]):
    raise ValueError("Missing required database configuration")

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
