"""
Email service module for sending emails using FastAPI-Mail.

Provides a clean interface for sending password reset emails and other
application notifications with proper error handling and logging.
"""

import logging
from datetime import UTC, datetime, timedelta

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

            # HTML template
            html_template = """
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Password Reset</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                    }
                    .header {
                        background-color: #f8f9fa;
                        padding: 20px;
                        text-align: center;
                        border-radius: 8px 8px 0 0;
                    }
                    .content {
                        background-color: #ffffff;
                        padding: 30px;
                        border: 1px solid #dee2e6;
                    }
                    .footer {
                        background-color: #f8f9fa;
                        padding: 20px;
                        text-align: center;
                        border-radius: 0 0 8px 8px;
                        border-top: 1px solid #dee2e6;
                    }
                    .btn {
                        display: inline-block;
                        background-color: #007bff;
                        color: #ffffff;
                        text-decoration: none;
                        padding: 12px 24px;
                        border-radius: 5px;
                        margin: 20px 0;
                        font-weight: bold;
                    }
                    .btn:hover {
                        background-color: #0056b3;
                    }
                    .warning {
                        background-color: #fff3cd;
                        border-left: 4px solid #ffc107;
                        padding: 12px;
                        margin: 20px 0;
                    }
                    .code {
                        font-family: monospace;
                        background-color: #f8f9fa;
                        padding: 2px 6px;
                        border-radius: 3px;
                        word-break: break-all;
                    }
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>🔐 Password Reset Request</h1>
                    <h2 style="color: #007bff; margin: 10px 0;">Radha Shyam Sundar Seva</h2>
                </div>

                <div class="content">
                    <p>Hello {% if user_name %}{{ user_name }}{% else %}there{% endif %},</p>

                    <p>We received a request to reset the password for your
                    Radha Shyam Sundar Seva account associated with <strong>{{ email }}</strong>.</p>

                    <p>To reset your password, click the button below:</p>

                    <div style="text-align: center;">
                        <a href="{{ reset_url }}" class="btn">Reset Password</a>
                    </div>

                    <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
                    <p class="code">{{ reset_url }}</p>

                    <div class="warning">
                        <strong>⚠️ Security Notice:</strong>
                        <ul>
                            <li>This link will expire in {{ expires_in }} hour(s) at {{ expiry_time }}</li>
                            <li>If you didn't request this reset, please ignore this email</li>
                            <li>Never share this link with anyone</li>
                        </ul>
                    </div>

                    <p>If you need help or have questions, please contact our support team.</p>

                    <p>Best regards,<br>The Uddhava Team</p>
                </div>

                <div class="footer">
                    <p style="margin: 0; font-size: 12px; color: #6c757d;">
                        This is an automated email. Please do not reply to this message.
                    </p>
                </div>
            </body>
            </html>
            """

            # Render template
            template = Template(html_template)
            html_content = template.render(
                user_name=user_name,
                email=email,
                reset_url=reset_url,
                expires_in=expires_in,
                expiry_time=expiry_time.strftime("%Y-%m-%d %H:%M UTC"),
            )

            # Create plain text fallback
            text_fallback = f"""
Password Reset Request - Radha Shyam Sundar Seva

Hello {user_name or "there"},

We received a request to reset the password for your Radha Shyam Sundar Seva account ({email}).

To reset your password, visit this link:
{reset_url}

This link will expire in {expires_in} hour(s) at {expiry_time.strftime("%Y-%m-%d %H:%M UTC")}.

Security Notice:
- If you didn't request this reset, please ignore this email
- Never share this link with anyone

Best regards,
The Radha Shyam Sundar Seva Team
            """.strip()

            # Create message with both HTML and text versions
            message = MessageSchema(
                subject=subject,
                recipients=[email],
                body=text_fallback,
                html=html_content,
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

    async def send_password_reset_confirmation(
        self, email: str, user_name: str | None = None
    ) -> bool:
        """
        Send confirmation email after successful password reset.

        Args:
            email: User's email address
            user_name: User's name (optional)

        Returns:
            bool: True if email sent successfully
        """
        try:
            subject = "Password Reset Successful - Uddhava"

            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2>Password Reset Successful</h2>
                <p>Hello {user_name or "there"},</p>
                <p>Your password has been successfully reset for your Uddhava account ({email}).</p>
                <p>If you did not make this change, please contact support immediately.</p>
                <p>Best regards,<br>The Uddhava Team</p>
            </div>
            """

            text_content = f"""
            Password Reset Successful

            Hello {user_name or "there"},

            Your password has been successfully reset for your Uddhava account ({email}).

            If you did not make this change, please contact support immediately.

            Best regards,
            The Uddhava Team
            """

            message = MessageSchema(
                subject=subject,
                recipients=[email],
                body=text_content,
                html=html_content,
                subtype=MessageType.html,
            )

            await self.fast_mail.send_message(message)

            logger.info(f"Password reset confirmation sent to {email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send confirmation email to {email}: {e!s}")
            # Don't raise exception for confirmation emails
            return False

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
            expires_in = settings.email_verification_token_expire_hours
            expiry_time = datetime.now(UTC) + timedelta(hours=expires_in)

            # Create email content
            subject = "Welcome to Radha Shyam Sundar Seva - Please Verify Your Email"

            # HTML template
            html_template = """
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Email Verification</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                    }
                    .header {
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        padding: 30px;
                        text-align: center;
                        border-radius: 8px 8px 0 0;
                    }
                    .content {
                        background-color: #ffffff;
                        padding: 30px;
                        border: 1px solid #dee2e6;
                    }
                    .footer {
                        background-color: #f8f9fa;
                        padding: 20px;
                        text-align: center;
                        border-radius: 0 0 8px 8px;
                        border-top: 1px solid #dee2e6;
                    }
                    .btn {
                        display: inline-block;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: #ffffff;
                        text-decoration: none;
                        padding: 15px 30px;
                        border-radius: 5px;
                        margin: 20px 0;
                        font-weight: bold;
                        font-size: 16px;
                    }
                    .btn:hover {
                        background: linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%);
                    }
                    .welcome-message {
                        background: linear-gradient(135deg, #e8f5e8 0%, #f0f8f0 100%);
                        border-left: 4px solid #28a745;
                        padding: 15px;
                        margin: 20px 0;
                        border-radius: 0 5px 5px 0;
                    }
                    .warning {
                        background-color: #fff3cd;
                        border-left: 4px solid #ffc107;
                        padding: 12px;
                        margin: 20px 0;
                    }
                    .code {
                        font-family: monospace;
                        background-color: #f8f9fa;
                        padding: 2px 6px;
                        border-radius: 3px;
                        word-break: break-all;
                    }
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>🙏 Welcome to the Family!</h1>
                    <h2 style="color: #ffd700; margin: 10px 0;">Radha Shyam Sundar Seva</h2>
                    <p style="margin: 0; opacity: 0.9;">Connecting devotees worldwide</p>
                </div>

                <div class="content">
                    <div class="welcome-message">
                        <p><strong>🎉 Hare Krishna {% if user_name %}{{ user_name }}{% else %}devotee{% endif %}!</strong></p>
                        <p>Welcome to our spiritual community. We're delighted you've joined us on this divine journey.</p>
                    </div>

                    <p>To complete your registration and activate your account for <strong>{{ email }}</strong>,
                    please verify your email address by clicking the button below:</p>

                    <div style="text-align: center;">
                        <a href="{{ verification_url }}" class="btn">✨ Verify My Email ✨</a>
                    </div>

                    <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
                    <p class="code">{{ verification_url }}</p>

                    <div class="warning">
                        <strong>⚠️ Important Notes:</strong>
                        <ul>
                            <li>This verification link will expire in {{ expires_in }} hour(s) at {{ expiry_time }}</li>
                            <li>Your account will remain inactive until email verification is complete</li>
                            <li>If you didn't create this account, please ignore this email</li>
                        </ul>
                    </div>

                    <p><strong>What happens next?</strong></p>
                    <ul>
                        <li>Click the verification link above</li>
                        <li>Your account will be activated instantly</li>
                        <li>Start exploring our devotee community features</li>
                        <li>Connect with fellow devotees worldwide</li>
                    </ul>

                    <p>If you need help or have questions, please contact our support team.</p>

                    <p>Radhe Radhe! 🌺<br>The Uddhava Team</p>
                </div>

                <div class="footer">
                    <p style="margin: 0 0 10px 0; font-size: 12px; color: #6c757d;">
                        This is an automated email. Please do not reply to this message.
                    </p>
                    <p style="margin: 0; font-size: 11px; color: #9ca3af;">
                        © {{ current_year }} Radha Shyam Sundar Seva. All rights reserved.
                    </p>
                </div>
            </body>
            </html>
            """

            # Render template
            template = Template(html_template)
            html_content = template.render(
                user_name=user_name,
                email=email,
                verification_url=verification_url,
                expires_in=expires_in,
                expiry_time=expiry_time.strftime("%Y-%m-%d %H:%M UTC"),
                current_year=datetime.now().year,
            )

            # Create plain text fallback
            text_fallback = f"""
Welcome to Radha Shyam Sundar Seva - Email Verification Required

Hare Krishna {user_name or "devotee"}!

Welcome to our spiritual community. We're delighted you've joined us on this divine journey.

To complete your registration and activate your account ({email}), please verify your email address by visiting this link:

{verification_url}

This verification link will expire in {expires_in} hour(s) at {expiry_time.strftime("%Y-%m-%d %H:%M UTC")}.

Important Notes:
- Your account will remain inactive until email verification is complete
- If you didn't create this account, please ignore this email

What happens next?
1. Click the verification link above
2. Your account will be activated instantly
3. Start exploring our devotee community features
4. Connect with fellow devotees worldwide

If you need help, please contact our support team.

Radhe Radhe!
The Uddhava Team

© {datetime.now().year} Radha Shyam Sundar Seva. All rights reserved.
            """.strip()

            # Create message with both HTML and text versions
            message = MessageSchema(
                subject=subject,
                recipients=[email],
                body=text_fallback,
                html=html_content,
                subtype=MessageType.html,
            )

            # Send email
            await self.fast_mail.send_message(message)

            logger.info(f"Email verification sent successfully to {email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email verification to {email}: {e!s}")
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
            subject = "Email Verified Successfully - Welcome to Radha Shyam Sundar Seva! 🎉"

            html_content = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Email Verified</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                    }}
                    .header {{
                        background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
                        color: white;
                        padding: 30px;
                        text-align: center;
                        border-radius: 8px 8px 0 0;
                    }}
                    .content {{
                        background-color: #ffffff;
                        padding: 30px;
                        border: 1px solid #dee2e6;
                    }}
                    .footer {{
                        background-color: #f8f9fa;
                        padding: 20px;
                        text-align: center;
                        border-radius: 0 0 8px 8px;
                        border-top: 1px solid #dee2e6;
                    }}
                    .success-message {{
                        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
                        border-left: 4px solid #28a745;
                        padding: 20px;
                        margin: 20px 0;
                        border-radius: 0 5px 5px 0;
                        text-align: center;
                    }}
                    .btn {{
                        display: inline-block;
                        background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
                        color: #ffffff;
                        text-decoration: none;
                        padding: 15px 30px;
                        border-radius: 5px;
                        margin: 20px 0;
                        font-weight: bold;
                    }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>✅ Email Verified Successfully!</h1>
                    <h2 style="color: #ffd700; margin: 10px 0;">Radha Shyam Sundar Seva</h2>
                </div>

                <div class="content">
                    <div class="success-message">
                        <h3>🎉 Congratulations {user_name or "devotee"}!</h3>
                        <p><strong>Your account is now fully activated</strong></p>
                    </div>

                    <p>Your email address <strong>{email}</strong> has been successfully verified.
                    Welcome to the Radha Shyam Sundar Seva community!</p>

                    <h3>🌟 What you can do now:</h3>
                    <ul>
                        <li><strong>Complete your profile</strong> - Add your spiritual journey details</li>
                        <li><strong>Connect with devotees</strong> - Find devotees in your area</li>
                        <li><strong>Track your practice</strong> - Monitor your chanting rounds</li>
                        <li><strong>Join events</strong> - Participate in community activities</li>
                        <li><strong>Access resources</strong> - Browse spiritual materials</li>
                    </ul>

                    <div style="text-align: center;">
                        <a href="{settings.frontend_login_url or "#"}" class="btn">🏠 Go to Dashboard</a>
                    </div>

                    <p>If you have any questions or need assistance, our support team is here to help.</p>

                    <p>Hare Krishna and welcome to our family! 🙏<br>The Uddhava Team</p>
                </div>

                <div class="footer">
                    <p style="margin: 0; font-size: 12px; color: #6c757d;">
                        This is an automated email. Please do not reply to this message.
                    </p>
                </div>
            </body>
            </html>
            """

            text_content = f"""
Email Verified Successfully - Welcome!

Congratulations {user_name or "devotee"}!

Your email address {email} has been successfully verified. Welcome to the Radha Shyam Sundar Seva community!

What you can do now:
- Complete your profile - Add your spiritual journey details
- Connect with devotees - Find devotees in your area
- Track your practice - Monitor your chanting rounds
- Join events - Participate in community activities
- Access resources - Browse spiritual materials

Visit: {settings.frontend_login_url or "your dashboard"}

If you have any questions, our support team is here to help.

Hare Krishna and welcome to our family!
The Uddhava Team
            """

            message = MessageSchema(
                subject=subject,
                recipients=[email],
                body=text_content,
                html=html_content,
                subtype=MessageType.html,
            )

            await self.fast_mail.send_message(message)

            logger.info(f"Email verification success confirmation sent to {email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send verification success email to {email}: {e!s}")
            # Don't raise exception for confirmation emails
            return False


# Global email service instance
email_service = EmailService()
