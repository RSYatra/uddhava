#!/usr/bin/env python3
"""
Test SMTP connection to Gmail from Render.
This script tests if Render can connect to Gmail's SMTP server.
"""

import asyncio
import sys
from datetime import datetime

import aiosmtplib


async def test_smtp_connection(server: str, port: int, timeout: int = 10):
    """Test SMTP connection without authentication."""
    print(f"\n{'=' * 70}")
    print("Testing SMTP Connection")
    print(f"{'=' * 70}")
    print(f"Server: {server}")
    print(f"Port: {port}")
    print(f"Timeout: {timeout}s")
    print(f"Time: {datetime.now()}")
    print(f"{'=' * 70}\n")

    try:
        print(f"[1/3] Attempting to connect to {server}:{port}...")

        smtp = aiosmtplib.SMTP(
            hostname=server,
            port=port,
            timeout=timeout,
            use_tls=False,
        )

        # Try to connect
        await smtp.connect()
        print(f"✅ SUCCESS: Connected to {server}:{port}")

        # Try EHLO/HELO
        print("\n[2/3] Sending EHLO command...")
        response = await smtp.ehlo()
        print(f"✅ EHLO Response: {response}")

        # Try STARTTLS
        print("\n[3/3] Testing STARTTLS...")
        await smtp.starttls()
        print("✅ STARTTLS successful")

        # Close connection
        await smtp.quit()

        print(f"\n{'=' * 70}")
        print("✅ ALL TESTS PASSED - Gmail SMTP is accessible!")
        print(f"{'=' * 70}\n")
        return True

    except TimeoutError:
        print(f"\n❌ TIMEOUT: Could not connect within {timeout} seconds")
        print("\nPossible causes:")
        print(f"  1. Render is blocking outbound connections to port {port}")
        print("  2. Firewall blocking SMTP traffic")
        print("  3. Network routing issue")
        print(f"\n{'=' * 70}\n")
        return False

    except ConnectionRefusedError:
        print("\n❌ CONNECTION REFUSED: Server rejected connection")
        print("\nPossible causes:")
        print(f"  1. Port {port} is blocked by Render")
        print("  2. Server not accepting connections from this IP")
        print(f"\n{'=' * 70}\n")
        return False

    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {e}")
        print(f"\n{'=' * 70}\n")
        return False


async def main():
    """Test multiple Gmail SMTP configurations."""
    print("\n" + "=" * 70)
    print("Gmail SMTP Connection Test")
    print("This will test if Render can connect to Gmail's SMTP servers")
    print("=" * 70 + "\n")

    tests = [
        ("smtp.gmail.com", 587, "Standard SMTP with STARTTLS"),
        ("smtp.gmail.com", 465, "SMTP with SSL"),
        ("smtp.gmail.com", 25, "Legacy SMTP (usually blocked)"),
    ]

    results = {}

    for server, port, description in tests:
        print(f"\n{'─' * 70}")
        print(f"Testing: {description}")
        print(f"{'─' * 70}")
        result = await test_smtp_connection(server, port, timeout=15)
        results[f"{server}:{port}"] = result
        await asyncio.sleep(1)  # Brief pause between tests

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for config, success in results.items():
        status = "✅ WORKING" if success else "❌ BLOCKED/FAILED"
        print(f"{config:30} {status}")

    print("=" * 70 + "\n")

    # Recommendations
    if results.get("smtp.gmail.com:587"):
        print("✅ Port 587 works - Your credentials might be wrong")
        print("   → Check MAIL_PASSWORD in Render environment variables")
        print("   → Make sure you're using Gmail App Password, not regular password")
    elif results.get("smtp.gmail.com:465"):
        print("✅ Port 465 works - Use SSL instead of STARTTLS")
        print("   → Update Render environment variables:")
        print("     MAIL_PORT=465")
        print("     MAIL_STARTTLS=false")
        print("     MAIL_SSL_TLS=true")
    else:
        print("❌ All ports blocked - Render doesn't allow Gmail SMTP")
        print("   → Must use alternative email service (SendGrid, Mailgun, AWS SES)")

    print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
