# Uddhava API

A production-ready FastAPI application for user management with photo upload functionality.

## Features

- User CRUD operations
- Photo upload with validation
- Email validation
- Database connection pooling
- Health monitoring
- Comprehensive logging
- Production-ready configuration

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

2. **Install production dependencies:**
   ```bash
   pip install -r requirements-prod.txt
   ```

3. **Start command:**
   ```bash
   ./start.sh
   ```

#### Using Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements-prod.txt .
RUN pip install -r requirements-prod.txt

COPY . .
EXPOSE 8000

CMD ["./start.sh"]
```

## API Endpoints

- `GET /` - API information
- `GET /health` - Health check
- `GET /users` - List users (with pagination)
- `POST /users` - Create user
- `GET /users/{id}` - Get specific user
- `GET /users/{id}/photo` - Get user photo
- `GET /docs` - API documentation (development only)

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

## Architecture

- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - Database ORM
- **MySQL** - Database with PyMySQL driver
- **Pydantic** - Data validation
- **pytest** - Testing framework
