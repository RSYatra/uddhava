#!/bin/bash

echo "========================================================================"
echo "RENDER SMTP DIAGNOSTIC SCRIPT"
echo "========================================================================"
echo ""
echo "This script will help diagnose why Gmail SMTP isn't working on Render"
echo ""
echo "Steps:"
echo "1. Add this script to your repo"
echo "2. Deploy to Render"
echo "3. SSH into Render service"
echo "4. Run this script"
echo ""
echo "========================================================================"
echo ""

# Test 1: Check if Python is available
echo "TEST 1: Checking Python..."
if command -v python3 &> /dev/null; then
    echo "✅ Python3 found: $(python3 --version)"
else
    echo "❌ Python3 not found"
fi
echo ""

# Test 2: Check DNS resolution
echo "TEST 2: Testing DNS resolution for smtp.gmail.com..."
if command -v nslookup &> /dev/null; then
    nslookup smtp.gmail.com | head -10
elif command -v host &> /dev/null; then
    host smtp.gmail.com
else
    echo "⚠️  DNS tools not available"
fi
echo ""

# Test 3: Check port connectivity (port 587)
echo "TEST 3: Testing connection to smtp.gmail.com:587..."
if command -v nc &> /dev/null; then
    timeout 5 nc -zv smtp.gmail.com 587 2>&1 || echo "❌ Cannot connect to port 587"
elif command -v telnet &> /dev/null; then
    timeout 5 telnet smtp.gmail.com 587 2>&1 | head -5 || echo "❌ Cannot connect to port 587"
else
    echo "⚠️  Network tools not available, using Python..."
    python3 -c "
import socket
import sys
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    result = sock.connect_ex(('smtp.gmail.com', 587))
    if result == 0:
        print('✅ Port 587 is open')
    else:
        print('❌ Port 587 is closed or filtered')
    sock.close()
except Exception as e:
    print(f'❌ Error: {e}')
    sys.exit(1)
"
fi
echo ""

# Test 4: Check port 465 (SSL)
echo "TEST 4: Testing connection to smtp.gmail.com:465..."
python3 -c "
import socket
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    result = sock.connect_ex(('smtp.gmail.com', 465))
    if result == 0:
        print('✅ Port 465 is open')
    else:
        print('❌ Port 465 is closed or filtered')
    sock.close()
except Exception as e:
    print(f'❌ Error: {e}')
" 2>/dev/null || echo "❌ Cannot test port 465"
echo ""

# Test 5: Check environment variables
echo "TEST 5: Checking email environment variables..."
ENV_VARS=("MAIL_USERNAME" "MAIL_PASSWORD" "MAIL_SERVER" "MAIL_PORT" "MAIL_FROM")
for var in "${ENV_VARS[@]}"; do
    if [ ! -z "${!var}" ]; then
        if [ "$var" = "MAIL_PASSWORD" ]; then
            echo "✅ $var is set (value hidden)"
        else
            echo "✅ $var = ${!var}"
        fi
    else
        echo "❌ $var is NOT set"
    fi
done
echo ""

# Test 6: Run Python SMTP test
echo "TEST 6: Running Python SMTP connection test..."
if [ -f "test_smtp_connection.py" ]; then
    python3 test_smtp_connection.py
else
    echo "⚠️  test_smtp_connection.py not found"
fi

echo ""
echo "========================================================================"
echo "DIAGNOSTIC COMPLETE"
echo "========================================================================"
echo ""
echo "Next steps based on results:"
echo "  - If ports are OPEN: Check Gmail credentials and App Password"
echo "  - If ports are BLOCKED: Render doesn't allow Gmail SMTP, use SendGrid"
echo "  - If environment variables missing: Add them in Render Dashboard"
echo ""
