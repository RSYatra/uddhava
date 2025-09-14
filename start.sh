#!/usr/bin/env bash
# Production startup script for Uddhava API
# Fast, idempotent launcher with optional safety checks.

set -euo pipefail

# Colors (optional, suppressed if NO_COLOR set)
if [[ -z "${NO_COLOR:-}" ]]; then
    GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
else
    GREEN=''; YELLOW=''; RED=''; NC=''
fi

log() { printf "%b[start.sh]%b %s\n" "$GREEN" "$NC" "$*"; }
warn() { printf "%b[warn]%b %s\n" "$YELLOW" "$NC" "$*"; }
err() { printf "%b[error]%b %s\n" "$RED" "$NC" "$*" >&2; }

# Determine project root (directory of this script)
SCRIPT_DIR="$( cd -- "${BASH_SOURCE[0]%/*}" >/dev/null 2>&1 && pwd )"
cd "$SCRIPT_DIR"

# Virtual environment detection (common names)
for vdir in venv .venv env; do
    if [[ -d "$vdir" && -f "$vdir/bin/activate" ]]; then
        # shellcheck disable=SC1090
        source "$vdir/bin/activate"
        log "Activated virtual environment: $vdir"
        break
    fi
done

if ! command -v uvicorn >/dev/null 2>&1; then
    err "uvicorn not found in PATH. Install dependencies first: pip install -r requirements.txt"
    exit 1
fi

# Default configuration
PORT=${PORT:-8000}
WORKERS=${WORKERS:-1}
HOST=${HOST:-0.0.0.0}
LOG_LEVEL=${LOG_LEVEL:-info}

PIDFILE=${PIDFILE:-server.pid}
FAST=${FAST:-0}            # FAST=1 skips DB check & port prompt (unless kill mode)
QUIET=${QUIET:-0}          # QUIET=1 reduces output
APP_IMPORT=${APP_IMPORT:-main:app}
EXTRA_UVICORN_ARGS=${EXTRA_UVICORN_ARGS:-}

usage() {
    cat <<EOF
Usage: ./start.sh [options]
Environment variables:
    PORT (default 8000)
    HOST (default 0.0.0.0)
    WORKERS (default 1)
    LOG_LEVEL (info|debug|warning|error)
    FAST=1                Skip port prompt & DB check
    ON_PORT_CONFLICT=kill|ignore|prompt (default prompt)
    PIDFILE=server.pid    File to store running PID
    QUIET=1               Minimal output
    APP_IMPORT=main:app   Uvicorn app import path
    EXTRA_UVICORN_ARGS    Additional uvicorn CLI args
RUN_MIGRATIONS=0        Run 'alembic upgrade head' before start when set to 1
Examples:
    FAST=1 ./start.sh
    ON_PORT_CONFLICT=kill WORKERS=4 LOG_LEVEL=info ./start.sh
    APP_IMPORT=main:app EXTRA_UVICORN_ARGS="--reload" ./start.sh
EOF
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help) usage; exit 0;;
        --fast) FAST=1; shift;;
        --quiet) QUIET=1; shift;;
        --kill) ON_PORT_CONFLICT=kill; shift;;
        --reload) EXTRA_UVICORN_ARGS="$EXTRA_UVICORN_ARGS --reload"; shift;;
        *) warn "Unknown argument: $1"; usage; exit 1;;
    esac
done

[[ $QUIET -eq 1 ]] || log "Starting Uddhava API"
[[ $QUIET -eq 1 ]] || log "Host: $HOST  Port: $PORT  Workers: $WORKERS  LogLevel: $LOG_LEVEL  Fast:$FAST"

# Port pre-check
if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    EXISTING_PID=$(lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t | head -n1)
    warn "Port $PORT already in use by PID $EXISTING_PID"
    MODE=${ON_PORT_CONFLICT:-prompt}
    # FAST mode converts prompt->kill for automation safety if ON_PORT_CONFLICT not explicitly set
    if [[ $FAST -eq 1 && $MODE == "prompt" ]]; then MODE=kill; fi
    case "$MODE" in
        kill)
            warn "Killing process $EXISTING_PID (ON_PORT_CONFLICT=kill)"
            kill "$EXISTING_PID" || { err "Failed to kill $EXISTING_PID"; exit 1; }
            sleep 1
            ;;
        ignore)
            warn "Continuing despite port conflict (may fail)"
            ;;
        prompt|*)
            read -r -p "Port $PORT in use by $EXISTING_PID. Kill it? [y/N]: " ans || ans="n"
            if [[ "$ans" =~ ^[Yy]$ ]]; then
                kill "$EXISTING_PID" || { err "Failed to kill $EXISTING_PID"; exit 1; }
                sleep 1
            else
                err "Aborting due to occupied port $PORT"
                exit 1
            fi
            ;;
    esac
fi

# Optional: run DB migrations (before connectivity check)
if [[ "${RUN_MIGRATIONS:-0}" == "1" ]]; then
    if command -v alembic >/dev/null 2>&1; then
        [[ $QUIET -eq 1 ]] || log "Running migrations (alembic upgrade head)"
        if ! alembic upgrade head; then
            err "Alembic migrations failed"
            exit 1
        fi
    else
        err "RUN_MIGRATIONS=1 but alembic not installed. Install dependencies including alembic."
        exit 1
    fi
fi

# Pre-flight: basic database connectivity (skip if FAST=1 or after failed migration)
if [[ "${SKIP_DB_CHECK:-0}" != "1" && $FAST -ne 1 ]]; then
    [[ $QUIET -eq 1 ]] || log "Checking database connectivity..."
    if python - <<'PY' 2>/dev/null
import os
os.environ['SKIP_DB_INIT'] = '1'  # Prevent table creation during check
from app.db.session import engine
from sqlalchemy import text
try:
        with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        print("DB connectivity: OK")
except Exception as e:
        print(f"DB connectivity check failed: {e}")
        exit(1)
PY
    then
        [[ $QUIET -eq 1 ]] || log "Database connectivity verified"
    else
        warn "Database connectivity failed - server will start without database features"
        warn "Database-dependent endpoints will return appropriate error responses"
        export SKIP_DB_INIT=1
    fi
fi

# PID file safety
if [[ -f "$PIDFILE" ]]; then
    OLD_PID=$(cat "$PIDFILE" 2>/dev/null || true)
    if [[ -n "$OLD_PID" && -d "/proc/$OLD_PID" ]]; then
        warn "Existing PID file $PIDFILE references running PID $OLD_PID"
    else
        rm -f "$PIDFILE"
    fi
fi

# Launch
[[ $QUIET -eq 1 ]] || log "Launching uvicorn ($APP_IMPORT)"

set +e
uvicorn $APP_IMPORT \
                --host "$HOST" \
                --port "$PORT" \
                --workers "$WORKERS" \
                --log-level "$LOG_LEVEL" \
                --access-log \
                --no-use-colors \
                $EXTRA_UVICORN_ARGS &
UV_PID=$!
set -e
echo $UV_PID > "$PIDFILE"
[[ $QUIET -eq 1 ]] || log "Server PID $UV_PID (pidfile: $PIDFILE)"

# Health wait (quick passive readiness) - use liveness check which doesn't require DB
if [[ ${WAIT_FOR_READY:-1} -eq 1 ]]; then
    [[ $QUIET -eq 1 ]] || log "Waiting for server to be ready..."
    for i in {1..20}; do
        # Try liveness endpoint first (doesn't require DB), fallback to root
        if curl -fsS "http://127.0.0.1:$PORT/api/v1/health/live" >/dev/null 2>&1 || \
           curl -fsS "http://127.0.0.1:$PORT/" >/dev/null 2>&1; then
            [[ $QUIET -eq 1 ]] || log "Server ready (health endpoint responded)"
            break
        fi
        sleep 0.2
    done
fi

if [[ ${FOREGROUND:-0} -eq 1 ]]; then
    wait $UV_PID
else
    [[ $QUIET -eq 1 ]] || log "Running in background (FG: FOREGROUND=1)"
fi

exit 0
