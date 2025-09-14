import logging
import os
import shutil
import time
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import EmailStr, ValidationError
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from database import SessionLocal, engine
from models import User, UserOut  # Base managed by Alembic migrations

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Reduce noisy third-party loggers if needed
for noisy in ["uvicorn.access"]:
    logging.getLogger(noisy).setLevel(logging.WARNING)

# NOTE: Schema management is now handled by Alembic migrations.
# For local first-run convenience you may uncomment the following line
# to auto-create tables in an empty dev database. In production, rely on
# `alembic upgrade head` instead of create_all.
# Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="Uddhava API",
    description="Backend APIs for user management system",
    version="1.0.0",
    docs_url="/docs" if os.getenv("ENVIRONMENT") != "production" else None,
    redoc_url="/redoc" if os.getenv("ENVIRONMENT") != "production" else None,
)

# Add CORS middleware for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Configuration
UPLOAD_DIR = Path("static")
UPLOAD_DIR.mkdir(exist_ok=True)
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif"}


def get_db():
    """Database dependency with robust error handling.

    Yields an active SQLAlchemy session and converts SQLAlchemy errors
    into HTTP 500 responses while logging full stack traces.
    """
    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError:
        # Capture full stack trace
        logger.exception("Database error during request")
        try:
            db.rollback()
        except Exception:
            logger.exception("Failed to rollback transaction")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred",
        )
    finally:
        db.close()


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):  # type: ignore
    """Log each request with a correlation ID and measure processing time.

    Adds X-Request-ID header so clients can report issues referencing logs.
    """
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start = time.time()
    logger.info(
        "--> %s %s id=%s client=%s",
        request.method,
        request.url.path,
        request_id,
        request.client.host if request.client else "-",
    )
    try:
        response = await call_next(request)
    except Exception:  # noqa: BLE001
        logger.exception("Unhandled exception processing request id=%s", request_id)
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal Server Error",
                "request_id": request_id,
            },
        )
    duration_ms = int((time.time() - start) * 1000)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time-ms"] = str(duration_ms)
    logger.info(
        "<-- %s %s id=%s status=%s time=%sms",
        request.method,
        request.url.path,
        request_id,
        response.status_code,
        duration_ms,
    )
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):  # type: ignore
    """Global fallback for uncaught exceptions.

    Ensures a consistent JSON response and logs full stack trace.
    """
    request_id = str(uuid.uuid4())
    logger.exception(
        "Global handler caught exception id=%s path=%s",
        request_id,
        request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "request_id": request_id},
    )


@app.get("/", tags=["Root"])
def read_root():
    """Root endpoint with basic API information"""
    return {
        "message": "Welcome to Uddhava API",
        "docs": "/docs",
        "version": "1.0.0",
        "status": "operational",
    }


@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Test database connection using proper context manager
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "connected",
            "environment": os.getenv("ENVIRONMENT", "development"),
        }
    except Exception:
        logger.exception("Health check failed")
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": "Database connection failed",
        }


@app.get("/users", response_model=List[UserOut], tags=["Users"])
def get_users(limit: int = 100, offset: int = 0, db: Session = Depends(get_db)):
    """Get all users with pagination"""
    try:
        users = db.query(User).offset(offset).limit(limit).all()
        logger.info(f"Retrieved {len(users)} users")
        return users
    except SQLAlchemyError:
        logger.exception("Error retrieving users")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users",
        )


@app.post("/users", response_model=UserOut, tags=["Users"])
def create_user(
    name: str = Form(..., min_length=1, max_length=255),
    email: str = Form(..., max_length=255),
    chanting_rounds: int = Form(..., ge=0, le=1000),
    photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    """Create a new user with optional photo upload"""
    try:
        # Validate email format using Pydantic model
        from pydantic import BaseModel

        class EmailValidator(BaseModel):
            email: EmailStr

        try:
            validator = EmailValidator(email=email.lower().strip())
            validated_email = validator.email
        except ValidationError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format",
            )

        # Check if email exists
        existing_user = db.query(User).filter(User.email == validated_email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        photo_path = None
        if photo and photo.filename:
            # Validate file size - handle case where size might be None
            file_size = getattr(photo, "size", None)
            if file_size is not None and file_size > MAX_FILE_SIZE:
                size_limit_mb = MAX_FILE_SIZE // (1024 * 1024)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File size exceeds {size_limit_mb}MB limit",
                )

            # Validate file type
            file_extension = Path(photo.filename).suffix.lower()
            if file_extension not in ALLOWED_EXTENSIONS:
                allowed = ", ".join(ALLOWED_EXTENSIONS)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid file type. Allowed: {allowed}",
                )

            # Save file with timestamp to prevent race conditions
            timestamp = str(int(time.time() * 1000))  # millisecond timestamp
            safe_filename = f"{validated_email}_{timestamp}_{photo.filename}"
            photo_path = UPLOAD_DIR / safe_filename

            try:
                with open(photo_path, "wb") as buffer:
                    shutil.copyfileobj(photo.file, buffer)
                logger.info(f"Photo saved: {photo_path}")
            except Exception as e:
                logger.error(f"Failed to save photo: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to save uploaded file",
                )

        # Create user
        user = User(
            name=name.strip(),
            email=validated_email,
            chanting_rounds=chanting_rounds,
            photo=str(photo_path) if photo_path else None,
        )

        try:
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"User created: {user.email}")
            return user
        except IntegrityError:
            logger.warning(
                "IntegrityError on user create (likely duplicate) %s",
                validated_email,
            )
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
        except Exception as db_error:
            # If user creation fails and we saved a file, clean it up
            if photo_path and photo_path.exists():
                try:
                    photo_path.unlink()
                    logger.info(f"Cleaned up orphaned file: {photo_path}")
                except Exception as cleanup_error:
                    logger.error(
                        f"Failed to cleanup file {photo_path}: {cleanup_error}"
                    )
            raise db_error

    except HTTPException:
        raise
    except Exception:
        logger.exception("Error creating user")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user",
        )


@app.get("/users/{user_id}/photo", tags=["Photos"])
def get_user_photo(user_id: int, db: Session = Depends(get_db)):
    """Get a user's photo by user ID"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        if not user.photo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User has no photo",
            )

        photo_path = Path(user.photo)
        if not photo_path.exists():
            logger.warning(f"Photo file missing: {photo_path}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Photo file not found",
            )

        # Check if file is readable
        if not os.access(photo_path, os.R_OK):
            logger.error(f"Photo file not readable: {photo_path}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Photo file cannot be accessed",
            )

        # Determine appropriate media type based on file extension
        file_extension = photo_path.suffix.lower()
        media_type_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
        }
        media_type = media_type_map.get(file_extension, "image/jpeg")

        return FileResponse(
            path=photo_path, media_type=media_type, filename=photo_path.name
        )

    except HTTPException:
        raise
    except Exception:
        logger.exception("Error retrieving photo for user %s", user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve photo",
        )


@app.get("/users/{user_id}", response_model=UserOut, tags=["Users"])
def get_user(user_id: int, db: Session = Depends(get_db)):
    """Get a specific user by ID"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        return user
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error retrieving user %s", user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user",
        )


# --- Debug / Diagnostics ---
@app.get("/debug/db", tags=["Debug"], include_in_schema=False)
def debug_db(token: Optional[str] = None):  # type: ignore
    """Lightweight DB diagnostics endpoint.

    Protection: requires query param ?token=<DEBUG_DB_TOKEN> if env var is set.
    Returns: basic connectivity + counts.
    """
    expected = os.getenv("DEBUG_DB_TOKEN")
    if expected and token != expected:
        raise HTTPException(status_code=403, detail="Forbidden")

    info: dict = {"status": "ok"}
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            result = conn.execute(text("SELECT COUNT(*) FROM users"))
            info["user_count"] = result.scalar() or 0
    except Exception as e:  # noqa: BLE001
        logger.exception("Debug DB check failed")
        info.update({"status": "error", "error": str(e)})
    return info


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting FastAPI server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)  # nosec B104
