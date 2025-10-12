"""
Diagnostic endpoints for debugging SMTP and other issues.
Only available in non-production environments for security.
"""

import logging
import socket
from datetime import datetime

import aiosmtplib
from fastapi import APIRouter

from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/diagnostics", tags=["Diagnostics"])


@router.get("/smtp-test", summary="Test SMTP Connection")
async def test_smtp_connection():
    """
    Test SMTP connectivity to Gmail servers.

    This endpoint tests:
    - Port 587 (STARTTLS)
    - Port 465 (SSL)
    - Port 25 (Legacy)

    Returns detailed results about which ports work.
    """
    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "server": "smtp.gmail.com",
        "tests": [],
        "summary": "",
        "recommendation": "",
    }

    # Test configurations
    test_configs = [
        {
            "port": 587,
            "name": "STARTTLS (Port 587)",
            "description": "Standard SMTP with STARTTLS",
        },
        {
            "port": 465,
            "name": "SSL (Port 465)",
            "description": "SMTP with SSL/TLS",
        },
        {
            "port": 25,
            "name": "Legacy (Port 25)",
            "description": "Usually blocked by cloud providers",
        },
    ]

    for config in test_configs:
        port = config["port"]
        test_result = {
            "port": port,
            "name": config["name"],
            "description": config["description"],
            "socket_test": "unknown",
            "smtp_test": "unknown",
            "error": None,
        }

        # Test 1: Basic socket connection
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(("smtp.gmail.com", port))
            sock.close()

            if result == 0:
                test_result["socket_test"] = "open"
            else:
                test_result["socket_test"] = "closed"
                test_result["error"] = f"Socket connection failed (code: {result})"
        except Exception as e:
            test_result["socket_test"] = "failed"
            test_result["error"] = f"Socket test error: {str(e)}"

        # Test 2: SMTP connection (only if socket is open)
        if test_result["socket_test"] == "open":
            try:
                smtp = aiosmtplib.SMTP(
                    hostname="smtp.gmail.com",
                    port=port,
                    timeout=10,
                    use_tls=(port == 465),
                )

                await smtp.connect()

                if port == 587:
                    await smtp.starttls()

                await smtp.quit()

                test_result["smtp_test"] = "success"
            except TimeoutError:
                test_result["smtp_test"] = "timeout"
                test_result["error"] = "SMTP connection timeout"
            except Exception as e:
                test_result["smtp_test"] = "failed"
                test_result["error"] = f"SMTP error: {type(e).__name__}: {str(e)}"

        results["tests"].append(test_result)

    # Generate summary and recommendation
    port_587_works = any(t["port"] == 587 and t["smtp_test"] == "success" for t in results["tests"])
    port_465_works = any(t["port"] == 465 and t["smtp_test"] == "success" for t in results["tests"])

    if port_587_works:
        results["summary"] = "✅ Port 587 (STARTTLS) works!"
        results["recommendation"] = (
            "Gmail SMTP is accessible. If emails still fail, check:\n"
            "1. MAIL_PASSWORD is Gmail App Password (not regular password)\n"
            "2. All environment variables are set in Render Dashboard\n"
            "3. MAIL_USERNAME matches MAIL_FROM"
        )
    elif port_465_works:
        results["summary"] = "✅ Port 465 (SSL) works, but not 587!"
        results["recommendation"] = (
            "Use SSL configuration instead of STARTTLS:\n"
            "Update Render environment variables:\n"
            "  MAIL_PORT=465\n"
            "  MAIL_STARTTLS=false\n"
            "  MAIL_SSL_TLS=true\n"
            "Keep all other MAIL_ variables the same."
        )
    else:
        results["summary"] = "❌ All Gmail SMTP ports are blocked"
        results["recommendation"] = (
            "Render blocks Gmail SMTP completely. Use SendGrid instead:\n"
            "1. Sign up: https://signup.sendgrid.com/\n"
            "2. Generate API key\n"
            "3. Update Render environment variables:\n"
            "   MAIL_SERVER=smtp.sendgrid.net\n"
            "   MAIL_PORT=587\n"
            "   MAIL_USERNAME=apikey\n"
            "   MAIL_PASSWORD=<your-sendgrid-api-key>"
        )

    return results


@router.get("/environment", summary="Check Environment Variables")
async def check_environment():
    """
    Check if all required email environment variables are set.

    Returns which variables are present (without showing values for security).
    """
    required_vars = [
        "MAIL_USERNAME",
        "MAIL_PASSWORD",
        "MAIL_FROM",
        "MAIL_SERVER",
        "MAIL_PORT",
        "MAIL_STARTTLS",
        "MAIL_SSL_TLS",
        "MAIL_USE_CREDENTIALS",
        "MAIL_VALIDATE_CERTS",
    ]

    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.environment,
        "variables": {},
        "missing": [],
        "all_set": True,
    }

    for var in required_vars:
        try:
            value = getattr(settings, var.lower())
            is_set = value is not None and value != ""

            results["variables"][var] = {
                "set": is_set,
                "type": type(value).__name__ if is_set else "None",
                # Show actual value only for non-sensitive settings
                "value": (
                    value
                    if var not in ["MAIL_PASSWORD", "MAIL_USERNAME"] and is_set
                    else "***HIDDEN***"
                    if is_set
                    else None
                ),
            }

            if not is_set:
                results["missing"].append(var)
                results["all_set"] = False
        except AttributeError:
            results["variables"][var] = {"set": False, "type": "missing"}
            results["missing"].append(var)
            results["all_set"] = False

    # Add recommendation
    if results["all_set"]:
        results["recommendation"] = "✅ All environment variables are set!"
    else:
        results["recommendation"] = (
            f"❌ Missing variables: {', '.join(results['missing'])}\n"
            "Add them in Render Dashboard → Environment → Add Environment Variable"
        )

    return results


@router.get("/email-config", summary="Show Email Configuration")
async def show_email_config():
    """
    Show current email configuration (without sensitive data).

    Useful for verifying configuration is loaded correctly.
    """
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "config": {
            "server": settings.mail_server,
            "port": settings.mail_port,
            "from": settings.mail_from,
            "username": settings.mail_username,
            "password": "***SET***" if settings.mail_password else "***NOT SET***",
            "starttls": settings.mail_starttls,
            "ssl_tls": settings.mail_ssl_tls,
            "use_credentials": settings.mail_use_credentials,
            "validate_certs": settings.mail_validate_certs,
        },
        "status": (
            "✅ Configuration loaded"
            if all(
                [
                    settings.mail_server,
                    settings.mail_port,
                    settings.mail_username,
                    settings.mail_password,
                ]
            )
            else "❌ Configuration incomplete"
        ),
    }


@router.get("/health-detailed", summary="Detailed Health Check")
async def detailed_health():
    """
    Comprehensive health check including database and email configuration.
    """
    from app.db.session import check_database_health

    db_health = check_database_health()

    email_configured = all(
        [
            settings.mail_server,
            settings.mail_port,
            settings.mail_username,
            settings.mail_password,
        ]
    )

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.environment,
        "app_version": settings.app_version,
        "database": {
            "status": db_health.get("status"),
            "response_time_ms": db_health.get("response_time_ms"),
            "pool_size": db_health.get("pool_size"),
        },
        "email": {
            "configured": email_configured,
            "server": settings.mail_server,
            "port": settings.mail_port,
        },
        "overall_status": (
            "healthy" if db_health.get("status") == "healthy" and email_configured else "degraded"
        ),
    }
