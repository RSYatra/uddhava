# Uddhava API

A production-ready FastAPI application with enterprise-grade features including structured logging, monitoring, performance optimization, and comprehensive validation.

## 🚀 Production Features

- **Structured Logging**: JSON formatted logs with rotation and performance timing
- **Database Reliability**: Connection pooling, automatic retries, and health monitoring
- **Input Validation**: Comprehensive sanitization and security validation
- **Monitoring & Metrics**: Health checks, performance tracking, and system metrics
- **Performance Optimization**: Async utilities, intelligent caching, and batch processing
- **Clean Architecture**: Service layer patterns and dependency management

> **For deployment:** See [PRODUCTION.md](PRODUCTION.md) for complete production deployment guide.

## Features

- User CRUD operations with advanced validation
- Photo upload with security validation
- Email validation and normalization
- Advanced database connection pooling with retry logic
- Comprehensive health monitoring with metrics endpoint
- Structured logging with JSON formatting and rotation
- Performance optimization with caching and async utilities
- Production-ready configuration management
- Startup automation script (`start.sh`) with health probe & port conflict handling
- Alembic migrations for schema management
- Diagnostic endpoints with monitoring capabilities
- Graceful error handling with structured responses

## Quick Start

### Local Development

1. **Clone and setup**
   ```bash
   git clone <repository-url>
   cd uddhava
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   export JWT_SECRET_KEY=$(openssl rand -hex 32)  # Generate secure JWT key
   ```

4. **Run the server**
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

5. **Alternative (recommended) launcher**
   ```bash
   ./start.sh --fast
   ```
   Flags:
   - `--fast` skips optional delays
   - `--kill` auto-kills existing process on the same port
   - `--reload` enables auto-reload (development only)
   - `--quiet` minimal logging during startup

### Production Deployment

See [PRODUCTION.md](PRODUCTION.md) for comprehensive production deployment guide.

#### Quick Deploy

**Option 1: Using render.yaml (Infrastructure as Code)**
1. Connect your GitHub repo to Render
2. Set environment variables in Render dashboard:
   - `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` - Database connection
   - `ENVIRONMENT=production`
   - `ALLOWED_ORIGINS` - Your frontend domains
3. Deploy automatically uses `render.yaml` configuration

**Option 2: Manual Web Service Setup**
1. Create a new Web Service in Render
2. **Build Command:** `pip install -r requirements.txt`
3. **Start Command:** `./start-render.sh` or `gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`
4. Set the same environment variables as above

#### Using Heroku

1. **Set environment variables:**
   - `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` - Database connection
   - `ENVIRONMENT=production`
   - `ALLOWED_ORIGINS` - Comma-separated list of allowed origins

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start command:**
   ```bash
   ./start.sh
   ``` photo upload functionality.

## Features

- User CRUD operations
- Photo upload with validation
- Email validation
- Database connection pooling
- Health monitoring
- Comprehensive logging
- Production-ready configuration
- Startup automation script (`start.sh`) with health probe & port conflict handling
- Alembic migrations for schema management
- Diagnostic endpoint (`/debug/db`) and standalone `debug_db.py`
- Graceful duplicate email handling and structured error responses

## Quick Start

### Local Development

1. **Clone and setup**
   ```bash
   git clone <repository-url>
   cd uddhava
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure database**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

4. **Run the server**
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

5. **Alternative (recommended) launcher**
   ```bash
   ./start.sh --fast
   ```
   Flags:
   - `--fast` skips optional delays
   - `--kill` auto-kills existing process on the same port
   - `--reload` enables auto-reload (development only)
   - `--quiet` minimal logging during startup

### Production Deployment

#### Using Render/Heroku

1. **Set environment variables:**
   - `DB_HOST` - Database host
   - `DB_PORT` - Database port (3306)
   - `DB_USER` - Database username
   - `DB_PASSWORD` - Database password
   - `DB_NAME` - Database name
   - `ENVIRONMENT` - Set to "production"
   - `ALLOWED_ORIGINS` - Comma-separated list of allowed origins

2. **Install dependencies:** (same single file used for all environments; dev-only tools are optional but safe in prod builds)
   ```bash
   pip install -r requirements.txt
   ```

3. **Start command:**
   ```bash
   ./start.sh
   ```

#### Using Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
   && pip uninstall -y black isort flake8 mypy bandit pytest pytest-cov pre-commit pip-audit || true

COPY . .
EXPOSE 8000

CMD ["./start.sh"]
```

## API Endpoints

### Core Endpoints
- `GET /` - API information and status
- `GET /health` - Basic health check
- `GET /metrics` - **NEW**: Comprehensive application metrics and monitoring
- `GET /docs` - Interactive API documentation (development only)

### User Management
- `GET /users` - List users (with advanced pagination and filtering)
- `POST /users` - Create user (with enhanced validation)
- `GET /users/{id}` - Get specific user
- `PUT /users/{id}` - Update user information
- `DELETE /users/{id}` - Delete user
- `GET /users/{id}/photo` - Get user photo
- `POST /users/{id}/photo` - Upload user photo (with security validation)

### Authentication
- `POST /auth/login` - User authentication
- `POST /auth/logout` - User logout
- `GET /auth/me` - Get current user profile

### Diagnostics
- `GET /debug/db` - Database diagnostics (requires `DEBUG_DB_TOKEN` if set)

## Development

### Setup pre-commit hooks
```bash
pre-commit install
```

### Run tests
```bash
pytest
```

### Code formatting
```bash
black .
isort .
flake8 .
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_HOST` | Database host | localhost |
| `DB_PORT` | Database port | 3306 |
| `DB_USER` | Database user | root |
| `DB_PASSWORD` | Database password | (required) |
| `DB_NAME` | Database name | uddhava_db |
| `ENVIRONMENT` | Environment (development/production) | development |
| `ALLOWED_ORIGINS` | CORS allowed origins | * |
| `SQL_DEBUG` | Enable SQL logging | false |
| `PORT` | Server port | 8000 |
| `WORKERS` | Number of workers | 1 |
| `DEBUG_DB_TOKEN` | Token required for /debug/db if set | (unset) |

## Architecture

- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - Database ORM
- **MySQL** - Database with PyMySQL driver
- **Pydantic** - Data validation
- **pytest** - Testing framework

## Security & Secrets

IMPORTANT: Real credentials must never be committed. The file `credentials.py` is ignored and only contains placeholder values now. Environment variables (see `.env.example`) take precedence and are the correct way to configure production or CI environments.

## Email Normalization

All user emails are normalized to lowercase and trimmed of leading/trailing whitespace at the ORM layer (SQLAlchemy event listeners on insert/update). This guarantees:

- Case-insensitive uniqueness (`User.email` unique index aligns with storage format)
- Consistent query behavior (`WHERE email = :value` works with lowercase input)
- Predictable audit/log formatting

Guidelines:
- Always compare and query using a lowercase email string.
- Do not attempt to preserve original casing for display—business accepted normalized storage.
- External inputs (forms, CSV imports) can pass mixed‑case; they will be normalized automatically.

If you introduce new ingestion paths (bulk loaders, raw SQL), rely on the same normalization by routing through ORM models or manually applying `lower().strip()`.

Previously committed database credentials should be considered compromised—rotate them immediately. After rotation, invalidate any long-lived connections (reset user password or drop and recreate user in MySQL).

Checklist before pushing a PR:
1. `git diff --name-only origin/main` shows no secrets or `.env` file
2. No personal images or PII in uploads (static/ directory auto-created and git-ignored)
4. Logs do not include sensitive data (emails are acceptable if business-approved)

## Diagnostics & Health

- `GET /health` validates database connectivity and reports environment
- `GET /debug/db` (optionally token-protected) returns connection status and user count
- `debug_db.py` can be run directly for quick CLI verification:
   ```bash
   python debug_db.py
   ```

## Database Migrations (Alembic)

The project uses Alembic for versioned, auditable schema changes.

Initial setup (existing database already has `users` table matching models):
```bash
alembic stamp 20250914_0001   # mark current DB at baseline revision
```

Fresh database (empty):
```bash
alembic upgrade head          # creates tables
```

Creating a new migration after model changes:
```bash
alembic revision --autogenerate -m "add new user field"
alembic upgrade head
```

Downgrade (use with care):
```bash
alembic downgrade -1
```

Automated on start (optional):
```bash
RUN_MIGRATIONS=1 ./start.sh --fast
```

Notes:
- `Base.metadata.create_all()` is disabled in `main.py`; rely on migrations.
- Never edit an existing migration once merged—add a new one.
- For destructive operations (dropping columns), create a two-phase migration (add new structure, backfill, remove old) to avoid downtime.

## Verification Steps After Clone

1. Create and activate virtual environment
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and set database values
4. Run `./start.sh --fast --kill`
5. Visit `http://localhost:8000/health` -> expect `{ "status": "healthy" }`
6. Create a user (POST `/users` via Swagger UI `/docs`)
7. List users `GET /users` -> includes new user
8. (Optional) Upload a photo -> retrieve via `/users/{id}/photo`
9. (Optional) Protect diagnostics: set `DEBUG_DB_TOKEN` then `GET /debug/db?token=...`

## Roadmap / Suggested Improvements

- Consolidated to single `requirements.txt` (DONE)
- Introduced Alembic migrations (DONE)
- Add unit/integration tests (users CRUD, photo upload, error cases)
- Implement optional default placeholder image for users without photos
- Add structured JSON logging or OpenTelemetry traces
- Enable log rotation (e.g., via `logging.handlers.RotatingFileHandler` or external aggregator)
- Add rate limiting or auth if exposed publicly
