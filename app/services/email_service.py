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


def _create_email_config():
    """Create email configuration with error handling."""
    try:
        return ConnectionConfig(
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
    except Exception as e:
        logger.error(f"Failed to create email configuration: {e}")
        raise


# Email configuration
try:
    conf = _create_email_config()
    logger.info(
        f"Email service configured: {settings.mail_server}:{settings.mail_port} "
        f"(STARTTLS={settings.mail_starttls}, SSL={settings.mail_ssl_tls})"
    )
except Exception as e:
    logger.error(f"Email configuration failed: {e}")
    conf = None


class EmailService:
    """Service for handling email operations."""

    def __init__(self):
        """Initialize the email service."""
        if conf is None:
            logger.error("Email configuration not available - email service disabled")
            raise HTTPException(
                status_code=503,
                detail="Email service is not configured. Please contact administrator.",
            )

        self.fast_mail = FastMail(conf)
        self.template_dir = Path(__file__).parent.parent.parent / "templates" / "emails"
        logger.debug(f"Email service initialized with template dir: {self.template_dir}")

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
        logger.info(f"Attempting to send password reset email to {email}")

        try:
            # Generate reset URL
            reset_url = f"{settings.password_reset_url_base}?token={reset_token}"
            logger.debug(f"Reset URL generated: {reset_url[:50]}...")

            # Calculate token expiration time
            expires_in = settings.password_reset_token_expire_hours
            expiry_time = datetime.now(UTC) + timedelta(hours=expires_in)

            # Create email content
            subject = "Password Reset Request - Radha Shyam Sundar Seva"

            # Load and render HTML template from file
            logger.debug("Loading password reset email template")
            html_template_content = self._load_template("password_reset.html")
            template = Template(html_template_content)
            html_content = template.render(
                user_name=user_name,
                email=email,
                reset_url=reset_url,
                expires_in=expires_in,
                expiry_time=expiry_time.strftime("%Y-%m-%d %H:%M UTC"),
            )
            logger.debug("Email template rendered successfully")

            # Create message with HTML content
            message = MessageSchema(
                subject=subject,
                recipients=[email],
                body=html_content,  # HTML content goes in body
                subtype=MessageType.html,
            )
            logger.debug(f"Sending email via SMTP: {settings.mail_server}:{settings.mail_port}")

            # Send email
            await self.fast_mail.send_message(message)

            logger.info(f"Password reset email sent successfully to {email}")
            return True

        except FileNotFoundError as e:
            logger.error(f"Email template not found: {e}")
            raise HTTPException(
                status_code=500,
                detail="Email template not found. Please contact administrator.",
            )
        except ConnectionRefusedError as e:
            logger.error(f"SMTP connection refused: {e}")
            raise HTTPException(
                status_code=503,
                detail="Email service temporarily unavailable. Please try again later.",
            )
        except TimeoutError as e:
            logger.error(f"SMTP connection timeout: {e}")
            raise HTTPException(
                status_code=504,
                detail="Email service timeout. Please try again later.",
            )
        except Exception as e:
            logger.error(
                f"Failed to send password reset email to {email}: {type(e).__name__}: {e!s}"
            )
            logger.exception("Full email error traceback:")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to send reset email: {type(e).__name__}. Please try again later or contact support.",
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
        logger.info(f"Attempting to send verification email to {email}")

        try:
            # Generate verification URL
            verification_url = f"{settings.email_verification_url_base}?token={verification_token}"
            logger.debug(f"Verification URL generated: {verification_url[:50]}...")

            # Calculate token expiration time
            expires_in = 24  # 24 hours
            expiry_time = datetime.now(UTC) + timedelta(hours=expires_in)

            # Create email content
            subject = "Email Verification - Radha Shyam Sundar Seva"

            # Load and render HTML template from file
            logger.debug("Loading email verification template")
            html_template_content = self._load_template("email_verification.html")
            template = Template(html_template_content)
            html_content = template.render(
                user_name=user_name,
                email=email,
                verification_url=verification_url,
                expires_in=expires_in,
                expiry_time=expiry_time.strftime("%Y-%m-%d %H:%M UTC"),
            )
            logger.debug("Email template rendered successfully")

            # Create message with HTML content
            message = MessageSchema(
                subject=subject,
                recipients=[email],
                body=html_content,  # HTML content goes in body
                subtype=MessageType.html,
            )
            logger.debug(f"Sending email via SMTP: {settings.mail_server}:{settings.mail_port}")

            # Send email
            await self.fast_mail.send_message(message)

            logger.info(f"Email verification sent successfully to {email}")
            return True

        except FileNotFoundError as e:
            logger.error(f"Email template not found: {e}")
            raise HTTPException(
                status_code=500,
                detail="Email template not found. Please contact administrator.",
            )
        except ConnectionRefusedError as e:
            logger.error(f"SMTP connection refused: {e}")
            raise HTTPException(
                status_code=503,
                detail="Email service temporarily unavailable. Please try again later.",
            )
        except TimeoutError as e:
            logger.error(f"SMTP connection timeout: {e}")
            raise HTTPException(
                status_code=504,
                detail="Email service timeout. Please try again later.",
            )
        except Exception as e:
            logger.error(f"Failed to send verification email to {email}: {type(e).__name__}: {e!s}")
            logger.exception("Full email error traceback:")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to send verification email: {type(e).__name__}. Please try again later or contact support.",
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
