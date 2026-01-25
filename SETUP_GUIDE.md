# Quick Setup Guide

## Prerequisites
- Python 3.9+
- MySQL 5.7+ or MariaDB
- Git

## Installation

### 1. Clone Repository
```bash
cd "/Users/ashupadhyay/Documents/HH BDDSM/Website"
# Already cloned as 'uddhava'
cd uddhava
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Setup Environment Variables
```bash
cp .env.example .env
# Edit .env with your settings:
# - Database credentials
# - JWT secret key
# - SMTP credentials (already set to Hostinger)
# - Frontend URL
```

### 5. Create Database
```bash
# Login to MySQL
mysql -u root -p
# OR with password
mysql -u root -pYourPassword

# Run in MySQL:
CREATE DATABASE uddhava_db;
EXIT;
```

### 6. Run Database Migrations
```bash
# Create tables using SQLAlchemy (in development)
python main.py
# Or use Alembic:
alembic upgrade head
```

## Running the Server

### Development
```bash
python main.py
# Or with Uvicorn:
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production
```bash
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker
```

## Access API
- **API Base URL**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/health

## Testing

### Test Signup
```bash
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "legal_name": "Test User",
    "email": "test@example.com",
    "password": "TestPass123!"
  }'
```

### Test Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123!"
  }'
```

### Test Health Check
```bash
curl http://localhost:8000/api/v1/health
```

## Email Configuration

The API uses SMTP for sending emails. Configuration is in `.env`:

```
SMTP_HOST=smtp.hostinger.com
SMTP_PORT=587
SMTP_USER=info@rsyatra.com
SMTP_PASSWORD=Devotee@108
SMTP_FROM_EMAIL=info@rsyatra.com
```

### Email Features
1. **Signup Verification Email**: Sent with 24-hour token
2. **Password Reset Email**: Sent with 1-hour token
3. **Verification Email Success**: Confirmation when email is verified

To test emails locally, check the application logs.

## Troubleshooting

### Database Connection Error
- Check `.env` database credentials
- Ensure MySQL is running
- Verify database exists: `mysql -u root -p -e "SHOW DATABASES;"`

### SMTP Connection Error
- Check SMTP credentials in `.env`
- Verify port 587 is accessible
- Check firewall settings
- Verify email credentials work with telnet/nc

### JWT Secret Key Warning
- Generate a secure key: `openssl rand -hex 32`
- Add to `.env`: `JWT_SECRET_KEY=your_generated_key`

### Port Already in Use
- Change port in `.env`: `PORT=8001`
- Or kill existing process: `lsof -i :8000 | grep LISTEN | awk '{print $2}' | xargs kill -9`

## Development Workflow

### Making Changes
1. Edit code
2. Server reloads automatically (with `--reload`)
3. Test via API docs or curl
4. Commit changes

### Git Workflow
```bash
# Check status
git status

# Stage changes
git add .

# Commit
git commit -m "feat: Your feature description"

# Push to testing branch
git push origin testing

# DO NOT commit to main/master - only testing branch
```

## Frontend Integration

The frontend is in `/Users/ashupadhyay/Documents/HH BDDSM/Website/rsyatra.web-ui-1`

### Development Flow
1. Run backend: `python main.py` (port 8000)
2. Run frontend: `npm run dev` in react-app directory (port 5173)
3. Frontend makes requests to `http://localhost:8000/api/v1/...`
4. Email verification links use frontend URL from `FRONTEND_URL` env var

## File Structure

```
uddhava/
├── app/
│   ├── api/
│   │   └── routes/
│   │       ├── auth.py          # Authentication endpoints
│   │       └── health.py        # Health check endpoint
│   ├── core/                    # Configuration and middleware
│   ├── db/
│   │   ├── models.py            # Database models
│   │   └── session.py           # Database session
│   ├── schemas/                 # Pydantic schemas
│   └── services/
│       └── smtp_service.py      # Email service
├── alembic/                     # Database migrations
├── main.py                      # FastAPI app entry point
├── requirements.txt             # Python dependencies
└── .env                         # Environment variables
```

## Next Steps

### Adding New Features
1. Create migration if database schema changes
2. Update models in `app/db/models.py`
3. Create new route file if needed: `app/api/routes/feature.py`
4. Register route in `main.py` under `register_routes()`
5. Add tests
6. Document in `API_ENDPOINTS.md`

### For Family Member Management
```python
# Already implemented in models.py
# Routes can be added in app/api/routes/family.py
```

### Database Backup
```bash
mysqldump -u root -p uddhava_db > backup.sql
```

### Database Restore
```bash
mysql -u root -p uddhava_db < backup.sql
```

## Additional Resources

- **Cleanup Summary**: See `CLEANUP_SUMMARY.md`
- **API Documentation**: See `API_ENDPOINTS.md`
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **SQLAlchemy Docs**: https://docs.sqlalchemy.org/
- **Alembic Docs**: https://alembic.sqlalchemy.org/

## Support

For issues or questions:
1. Check logs in `logs/` directory
2. Review error in API response
3. Check `.env` configuration
4. Verify database and SMTP connectivity
5. Check git branch is `testing`
