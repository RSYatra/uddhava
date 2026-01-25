"""
SMTP email service for sending emails via Hostinger.

Replaces Gmail authentication with direct SMTP connection.
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class SMTPService:
    """
    Email service using SMTP (Hostinger configuration).
    """

    def __init__(self):
        self.smtp_host = settings.SMTP_HOST or "smtp.hostinger.com"
        self.smtp_port = settings.SMTP_PORT or 587
        self.smtp_user = settings.SMTP_USER or "info@rsyatra.com"
        self.smtp_password = settings.SMTP_PASSWORD or ""
        self.from_email = settings.SMTP_FROM_EMAIL or "info@rsyatra.com"
        self.from_name = "RSYatra"

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        plain_text_content: Optional[str] = None,
    ) -> bool:
        """
        Send an email via SMTP.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email body
            plain_text_content: Plain text fallback (optional)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = to_email

            # Add plain text and HTML parts
            if plain_text_content:
                msg.attach(MIMEText(plain_text_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))

            # Send via SMTP
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()  # Use TLS encryption
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except smtplib.SMTPAuthenticationError:
            logger.error("SMTP authentication failed. Check credentials.")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False

    async def send_verification_email(
        self,
        to_email: str,
        user_name: str,
        verification_token: str,
    ) -> bool:
        """
        Send email verification link.

        Args:
            to_email: User email
            user_name: User's display name
            verification_token: Token for email verification

        Returns:
            True if successful
        """
        verification_url = f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"

        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2>Welcome to RSYatra, {user_name}!</h2>
                    <p>Thank you for signing up. Please verify your email address to activate your account.</p>
                    
                    <div style="margin: 30px 0;">
                        <a href="{verification_url}" style="background-color: #4CAF50; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block;">
                            Verify Email
                        </a>
                    </div>
                    
                    <p>Or copy and paste this link in your browser:</p>
                    <p style="word-break: break-all; color: #0066cc;">{verification_url}</p>
                    
                    <p style="margin-top: 40px; color: #666; font-size: 12px;">
                        This link expires in 24 hours. If you didn't create this account, please ignore this email.
                    </p>
                </div>
            </body>
        </html>
        """

        plain_text = f"""
        Welcome to RSYatra, {user_name}!

        Please verify your email by visiting:
        {verification_url}

        This link expires in 24 hours.
        """

        return await self.send_email(
            to_email=to_email,
            subject="Verify Your RSYatra Email",
            html_content=html_content,
            plain_text_content=plain_text,
        )

    async def send_password_reset_email(
        self,
        to_email: str,
        user_name: str,
        reset_token: str,
    ) -> bool:
        """
        Send password reset link.

        Args:
            to_email: User email
            user_name: User's display name
            reset_token: Token for password reset

        Returns:
            True if successful
        """
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"

        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2>Password Reset Request</h2>
                    <p>Hi {user_name},</p>
                    <p>We received a request to reset your password. Click the link below to create a new password.</p>
                    
                    <div style="margin: 30px 0;">
                        <a href="{reset_url}" style="background-color: #2196F3; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block;">
                            Reset Password
                        </a>
                    </div>
                    
                    <p>Or copy and paste this link in your browser:</p>
                    <p style="word-break: break-all; color: #0066cc;">{reset_url}</p>
                    
                    <p style="margin-top: 40px; color: #666; font-size: 12px;">
                        This link expires in 1 hour. If you didn't request this, please ignore this email.
                    </p>
                </div>
            </body>
        </html>
        """

        plain_text = f"""
        Password Reset Request

        Visit this link to reset your password:
        {reset_url}

        This link expires in 1 hour.
        """

        return await self.send_email(
            to_email=to_email,
            subject="Reset Your RSYatra Password",
            html_content=html_content,
            plain_text_content=plain_text,
        )
