"""
Gmail API service for sending emails using OAuth2.
More reliable than SMTP and works on platforms that block SMTP ports.
"""

import base64
import logging
import pickle  # nosec B403 - Required for Google OAuth2 credentials
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from fastapi import HTTPException
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from jinja2 import Template

from app.core.config import settings

logger = logging.getLogger(__name__)


class GmailService:
    """Service for sending emails via Gmail API with OAuth2."""

    def __init__(self):
        """Initialize Gmail API service."""
        self.credentials = self._load_credentials()
        self.service = None
        if self.credentials:
            try:
                self.service = build("gmail", "v1", credentials=self.credentials)
                logger.info("Gmail API service initialized successfully")
            except Exception as e:
                logger.error(f"Failed to build Gmail service: {e}")
                raise HTTPException(
                    status_code=503,
                    detail="Gmail API service unavailable",
                )
        self.template_dir = Path(__file__).parent.parent.parent / "templates" / "emails"

    def _load_credentials(self) -> Credentials | None:
        """Load OAuth2 credentials from token.pickle or token.json file."""
        try:
            creds_path = Path(settings.gmail_credentials_file)
            if not creds_path.exists():
                logger.error(f"Credentials file not found: {creds_path}")
                raise HTTPException(
                    status_code=503,
                    detail="Gmail credentials not configured",
                )

            # Support both pickle and JSON formats
            if creds_path.suffix == ".json":
                # Load from JSON (more reliable for cloud deployments)
                import json

                with open(creds_path) as f:
                    creds_dict = json.load(f)

                creds = Credentials(
                    token=creds_dict.get("token"),
                    refresh_token=creds_dict.get("refresh_token"),
                    token_uri=creds_dict.get("token_uri"),
                    client_id=creds_dict.get("client_id"),
                    client_secret=creds_dict.get("client_secret"),
                    scopes=creds_dict.get("scopes"),
                )
                logger.info("Loaded Gmail credentials from JSON")
            else:
                # Load from pickle (backward compatibility)
                with open(creds_path, "rb") as token:
                    creds = pickle.load(token)  # nosec B301 - Safe: loading our own OAuth2 credentials
                logger.info("Loaded Gmail credentials from pickle")

            # Refresh token if expired
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logger.info("Gmail credentials refreshed")

                    # Save refreshed credentials (JSON only, pickle stays read-only)
                    if creds_path.suffix == ".json":
                        import json

                        creds_dict = {
                            "token": creds.token,
                            "refresh_token": creds.refresh_token,
                            "token_uri": creds.token_uri,
                            "client_id": creds.client_id,
                            "client_secret": creds.client_secret,
                            "scopes": creds.scopes,
                        }
                        with open(creds_path, "w") as f:
                            json.dump(creds_dict, f)
                        logger.info("Saved refreshed credentials to JSON")

                except Exception as e:
                    logger.error(f"Failed to refresh credentials: {e}")
                    raise HTTPException(
                        status_code=503,
                        detail="Gmail credentials expired",
                    )

            return creds

        except FileNotFoundError:
            logger.error("Gmail credentials file not found")
            raise HTTPException(
                status_code=503,
                detail="Gmail credentials not found",
            )
        except Exception as e:
            logger.error(f"Error loading Gmail credentials: {e}")
            logger.exception("Full traceback:")
            raise HTTPException(
                status_code=503,
                detail=f"Gmail credentials error: {type(e).__name__}",
            )

    def _load_template(self, template_name: str) -> str:
        """Load email template from file."""
        template_path = self.template_dir / template_name

        if not template_path.exists():
            logger.error(f"Email template not found: {template_path}")
            raise FileNotFoundError(f"Email template not found: {template_name}")

        with open(template_path, encoding="utf-8") as f:
            return f.read()

    def _create_message(self, to: str, subject: str, html_content: str) -> dict:
        """Create email message in Gmail API format."""
        message = MIMEMultipart("alternative")
        message["From"] = f"{settings.gmail_from_name} <{settings.gmail_from_email}>"
        message["To"] = to
        message["Subject"] = subject

        html_part = MIMEText(html_content, "html")
        message.attach(html_part)

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        return {"raw": raw_message}

    async def send_email(self, to: str, subject: str, html_content: str) -> bool:
        """
        Send email via Gmail API.

        Args:
            to: Recipient email address
            subject: Email subject
            html_content: HTML content of email

        Returns:
            bool: True if sent successfully

        Raises:
            HTTPException: If sending fails
        """
        logger.info(f"Sending email to {to}: {subject}")

        try:
            if not self.service:
                raise HTTPException(
                    status_code=503,
                    detail="Gmail service not initialized",
                )

            message = self._create_message(to, subject, html_content)

            self.service.users().messages().send(userId="me", body=message).execute()

            logger.info(f"Email sent successfully to {to}")
            return True

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to send email to {to}: {type(e).__name__}: {e}")
            logger.exception("Full error traceback:")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to send email: {type(e).__name__}",
            )

    async def send_password_reset_email(
        self, email: str, reset_token: str, user_name: str | None = None
    ) -> bool:
        """Send password reset email."""
        from datetime import UTC, datetime, timedelta

        logger.info(f"Sending password reset email to {email}")

        reset_url = f"{settings.password_reset_url_base}?token={reset_token}"
        expires_in = settings.password_reset_token_expire_hours
        expiry_time = datetime.now(UTC) + timedelta(hours=expires_in)

        html_template = self._load_template("password_reset.html")
        template = Template(html_template)
        html_content = template.render(
            user_name=user_name,
            email=email,
            reset_url=reset_url,
            expires_in=expires_in,
            expiry_time=expiry_time.strftime("%Y-%m-%d %H:%M UTC"),
        )

        subject = "Password Reset Request - Radha Shyam Sundar Seva"
        return await self.send_email(email, subject, html_content)

    async def send_email_verification(
        self, email: str, verification_token: str, user_name: str | None = None
    ) -> bool:
        """Send email verification email."""
        from datetime import UTC, datetime, timedelta

        logger.info(f"Sending verification email to {email}")

        verification_url = f"{settings.email_verification_url_base}?token={verification_token}"
        expires_in = 24
        expiry_time = datetime.now(UTC) + timedelta(hours=expires_in)

        html_template = self._load_template("email_verification.html")
        template = Template(html_template)
        html_content = template.render(
            user_name=user_name,
            email=email,
            verification_url=verification_url,
            expires_in=expires_in,
            expiry_time=expiry_time.strftime("%Y-%m-%d %H:%M UTC"),
        )

        subject = "Email Verification - Radha Shyam Sundar Seva"
        return await self.send_email(email, subject, html_content)

    async def send_email_verification_success(
        self, email: str, user_name: str | None = None
    ) -> bool:
        """Send confirmation email after successful verification."""
        logger.info(f"Sending verification success email to {email}")

        try:
            login_url = settings.frontend_login_url

            html_template = self._load_template("email_verification_success.html")
            template = Template(html_template)
            html_content = template.render(
                user_name=user_name,
                email=email,
                login_url=login_url,
            )

            subject = "Email Verified - Radha Shyam Sundar Seva"
            return await self.send_email(email, subject, html_content)

        except Exception as e:
            logger.error(f"Failed to send verification success email: {e}")
            return False
