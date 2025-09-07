import logging
import os
import shutil
from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from database import SessionLocal, engine
from models import Base, User, UserOut

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create database tables
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
except Exception as e:
    logger.error(f"Failed to create database tables: {e}")
    raise

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
    """Database dependency"""
    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred",
        )
    finally:
        db.close()


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
        # Test database connection
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()

        return {
            "status": "healthy",
            "database": "connected",
            "environment": os.getenv("ENVIRONMENT", "development"),
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
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
    except SQLAlchemyError as e:
        logger.error(f"Error retrieving users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users",
        )


@app.post("/users", response_model=UserOut, tags=["Users"])
def create_user(
    name: str = Form(..., min_length=1, max_length=255),
    email: str = Form(...),
    chanting_rounds: int = Form(..., ge=0, le=1000),
    photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    """Create a new user with optional photo upload"""
    try:
        # Check if email exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        photo_path = None
        if photo and photo.filename:
            # Validate file size
            if photo.size and photo.size > MAX_FILE_SIZE:
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

            # Save file
            safe_filename = f"{email}_{photo.filename}"
            photo_path = UPLOAD_DIR / safe_filename

            with open(photo_path, "wb") as buffer:
                shutil.copyfileobj(photo.file, buffer)

            logger.info(f"Photo saved: {photo_path}")

        # Create user
        user = User(
            name=name.strip(),
            email=email.lower().strip(),
            chanting_rounds=chanting_rounds,
            photo=str(photo_path) if photo_path else None,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        logger.info(f"User created: {user.email}")
        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {e}")
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
                status_code=status.HTTP_404_NOT_FOUND, detail="User has no photo"
            )

        photo_path = Path(user.photo)
        if not photo_path.exists():
            logger.warning(f"Photo file missing: {photo_path}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Photo file not found"
            )

        return FileResponse(
            path=photo_path, media_type="image/jpeg", filename=photo_path.name
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving photo for user {user_id}: {e}")
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
    except Exception as e:
        logger.error(f"Error retrieving user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user",
        )


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting FastAPI server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)  # nosec B104
