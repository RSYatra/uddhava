from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class User(Base):
    """User database model"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    chanting_rounds = Column(Integer, nullable=False)
    photo = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class UserCreate(BaseModel):
    """Pydantic model for user creation"""

    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    chanting_rounds: int = Field(..., ge=0, le=1000)


class UserOut(BaseModel):
    """Pydantic model for user response"""

    id: int
    name: str
    email: str
    chanting_rounds: int
    photo: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
