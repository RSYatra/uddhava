"""
Email service module for sending emails using FastAPI-Mail.

Provides a clean interface for sending password reset emails and other
application notifications with proper error handling and logging.
"""

import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import HTTPException
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from jinja2 import Template

from app.core.config import settings

logger = logging.getLogger(__name__)

# Email configuration
conf = ConnectionConfig(
    MAIL_USERNAME=settings.mail_username,
    MAIL_PASSWORD=settings.mail_password,
    MAIL_FROM=settings.mail_from,
    MAIL_PORT=settings.mail_port,
    MAIL_SERVER=settings.mail_server,
    MAIL_STARTTLS=settings.mail_starttls,
    MAIL_SSL_TLS=settings.mail_ssl_tls,
    USE_CREDENTIALS=settings.mail_use_credentials,
    VALIDATE_CERTS=settings.mail_validate_certs,
)


class EmailService:
    """Service for handling email operations."""

    def __init__(self):
        """Initialize the email service."""
        self.fast_mail = FastMail(conf)
        self.template_dir = Path(__file__).parent.parent.parent / "templates" / "emails"

    def _load_template(self, template_name: str) -> str:
        """Load email template from file.

        Args:
            template_name: Name of the template file (e.g., 'password_reset.html')

        Returns:
            str: Template content

        Raises:
            FileNotFoundError: If template file doesn't exist
        """
        template_path = self.template_dir / template_name

        if not template_path.exists():
            logger.error(f"Email template not found: {template_path}")
            raise FileNotFoundError(f"Email template not found: {template_name}")

        with open(template_path, encoding="utf-8") as f:
            return f.read()

    async def send_password_reset_email(
        self, email: str, reset_token: str, user_name: str | None = None
    ) -> bool:
        """
        Send password reset email to user.

        Args:
            email: User's email address
            reset_token: Password reset token
            user_name: User's name (optional)

        Returns:
            bool: True if email sent successfully

        Raises:
            HTTPException: If email sending fails
        """
        try:
            # Generate reset URL
            reset_url = f"{settings.password_reset_url_base}?token={reset_token}"

            # Calculate token expiration time
            expires_in = settings.password_reset_token_expire_hours
            expiry_time = datetime.now(UTC) + timedelta(hours=expires_in)

            # Create email content
            subject = "Password Reset Request - Radha Shyam Sundar Seva"

            # Load and render HTML template from file
            html_template_content = self._load_template("password_reset.html")
            template = Template(html_template_content)
            html_content = template.render(
                user_name=user_name,
                email=email,
                reset_url=reset_url,
                expires_in=expires_in,
                expiry_time=expiry_time.strftime("%Y-%m-%d %H:%M UTC"),
            )

            # Create message with HTML content
            message = MessageSchema(
                subject=subject,
                recipients=[email],
                body=html_content,  # HTML content goes in body
                subtype=MessageType.html,
            )

            # Send email
            await self.fast_mail.send_message(message)

            logger.info(f"Password reset email sent successfully to {email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send password reset email to {email}: {e!s}")
            raise HTTPException(
                status_code=500,
                detail="Failed to send reset email. Please try again later.",
            )

    async def send_email_verification(
        self,
        email: str,
        verification_token: str,
        user_name: str | None = None,
    ) -> bool:
        """
        Send email verification email to user.

        Args:
            email: User's email address
            verification_token: Email verification token
            user_name: User's name (optional)

        Returns:
            bool: True if email sent successfully

        Raises:
            HTTPException: If email sending fails
        """
        try:
            # Generate verification URL
            verification_url = f"{settings.email_verification_url_base}?token={verification_token}"

            # Calculate token expiration time
            expires_in = 24  # 24 hours
            expiry_time = datetime.now(UTC) + timedelta(hours=expires_in)

            # Create email content
            subject = "Email Verification - Radha Shyam Sundar Seva"

            # Load and render HTML template from file
            html_template_content = self._load_template("email_verification.html")
            template = Template(html_template_content)
            html_content = template.render(
                user_name=user_name,
                email=email,
                verification_url=verification_url,
                expires_in=expires_in,
                expiry_time=expiry_time.strftime("%Y-%m-%d %H:%M UTC"),
            )

            # Create message with HTML content
            message = MessageSchema(
                subject=subject,
                recipients=[email],
                body=html_content,  # HTML content goes in body
                subtype=MessageType.html,
            )

            # Send email
            await self.fast_mail.send_message(message)

            logger.info(f"Email verification sent successfully to {email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send verification email to {email}: {e!s}")
            raise HTTPException(
                status_code=500,
                detail="Failed to send verification email. Please try again later.",
            )

    async def send_email_verification_success(
        self, email: str, user_name: str | None = None
    ) -> bool:
        """
        Send confirmation email after successful email verification.

        Args:
            email: User's email address
            user_name: User's name (optional)

        Returns:
            bool: True if email sent successfully
        """
        try:
            # Create email content
            subject = "Email Verified - Radha Shyam Sundar Seva"

            # Generate login URL
            login_url = settings.frontend_login_url

            # Load and render HTML template from file
            html_template_content = self._load_template("email_verification_success.html")
            template = Template(html_template_content)
            html_content = template.render(
                user_name=user_name,
                email=email,
                login_url=login_url,
            )

            # Create message with HTML content
            message = MessageSchema(
                subject=subject,
                recipients=[email],
                body=html_content,  # HTML content goes in body
                subtype=MessageType.html,
            )

            # Send email
            await self.fast_mail.send_message(message)

            logger.info(f"Email verification success confirmation sent to {email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send verification success email to {email}: {e!s}")
            # Don't raise exception for confirmation emails
            return False
