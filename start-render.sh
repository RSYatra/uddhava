#!/bin/bash
# Render deployment start script

# Run migrations if configured
if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
    echo "Running database migrations..."
    alembic upgrade head
fi

# Start the FastAPI application with gunicorn
exec gunicorn main:app \
    -w 4 \
    -k uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:${PORT:-8000} \
    --log-level info \
    --access-logfile - \
    --error-logfile -
