#!/bin/bash
# Production startup script for Uddhava API

set -e  # Exit on any error

# Set default values
PORT=${PORT:-8000}
WORKERS=${WORKERS:-1}
HOST=${HOST:-0.0.0.0}

echo "Starting Uddhava API..."
echo "Host: $HOST"
echo "Port: $PORT"
echo "Workers: $WORKERS"

# Start the FastAPI server with production settings
uvicorn main:app \
    --host $HOST \
    --port $PORT \
    --workers $WORKERS \
    --access-log \
    --no-use-colors
