"""Minimal authentication routes (conservative) for signup, email verification, and password reset.

This file is intentionally small and safe: it reuses existing DB/session and email
services where available but does not remove any existing code.
"""

from datetime import datetime, timedelta
import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Devotee
from app.services.gmail_service import GmailService
from app.core.security import get_password_hash, verify_password
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Minimal Auth"])


def _generate_token() -> str:
    return secrets.token_urlsafe(32)


@router.post("/signup")
async def signup(request: Request, payload: dict, db: Session = Depends(get_db)):
    """Create a minimal unverified user and send verification email (dev: logs email)."""
    email = payload.get("email", "").strip().lower()
    legal_name = payload.get("legal_name", "").strip()
    password = payload.get("password", "")

    if not email or not legal_name or not password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing fields")

    existing = db.query(Devotee).filter(Devotee.email == email).first()
    if existing:
        return JSONResponse(status_code=409, content={"success": False, "message": "Email exists"})

    password_hash = get_password_hash(password)
    token = _generate_token()

    user = Devotee(
        legal_name=legal_name,
        email=email,
        password_hash=password_hash,
        email_verified=False,
        verification_token=token,
        verification_expires=datetime.utcnow() + timedelta(hours=24),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # send verification
    try:
        gmail = GmailService()
        await gmail.send_email_verification(email=email, verification_token=token, user_name=legal_name)
    except Exception:
        logger.exception("Failed to send verification email (logged for dev)")

    return {"success": True, "message": "Signup created. Check email for verification."}


@router.get("/verify-email")
async def verify_email(token: str, db: Session = Depends(get_db)):
    user = db.query(Devotee).filter(Devotee.verification_token == token).first()
    if not user:
        raise HTTPException(status_code=404, detail="Invalid token")
    if user.email_verified:
        return {"success": True, "message": "Already verified"}
    if user.verification_expires and user.verification_expires < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Token expired")

    user.email_verified = True
    user.verification_token = None
    user.verification_expires = None
    db.add(user)
    db.commit()

    try:
        gmail = GmailService()
        await gmail.send_email_verification_success(email=user.email, user_name=user.legal_name)
    except Exception:
        logger.exception("Failed to send verification success email")

    return {"success": True, "message": "Email verified"}


@router.post("/forgot-password")
async def forgot_password(payload: dict, db: Session = Depends(get_db)):
    email = payload.get("email", "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Missing email")
    user = db.query(Devotee).filter(Devotee.email == email).first()
    if not user:
        # Don't reveal existence
        return {"success": True, "message": "If that email exists, a reset link was sent."}

    token = _generate_token()
    user.password_reset_token = token
    user.password_reset_expires = datetime.utcnow() + timedelta(hours=2)
    db.add(user)
    db.commit()

    try:
        gmail = GmailService()
        await gmail.send_password_reset_email(email=email, reset_token=token, user_name=user.legal_name)
    except Exception:
        logger.exception("Failed to send password reset email")

    return {"success": True, "message": "If that email exists, a reset link was sent."}


@router.post("/reset-password")
async def reset_password(payload: dict, db: Session = Depends(get_db)):
    token = payload.get("token")
    new_password = payload.get("password")
    if not token or not new_password:
        raise HTTPException(status_code=400, detail="Missing token or password")

    user = db.query(Devotee).filter(Devotee.password_reset_token == token).first()
    if not user:
        raise HTTPException(status_code=404, detail="Invalid token")
    if user.password_reset_expires and user.password_reset_expires < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Token expired")

    user.password_hash = get_password_hash(new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    db.add(user)
    db.commit()

    return {"success": True, "message": "Password updated"}
