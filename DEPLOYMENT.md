# Deployment Configuration Guide

## Issue: Email URLs pointing to localhost instead of production domain

### Problem
- Local server: URLs work correctly (https://rsyatra.com/verify-email)
- Deployed server: URLs point to localhost (http://localhost:3000/verify-email)

### Root Cause
The application is using default configuration values instead of environment-specific values.

## Solution Options

### Option 1: Environment Variables (Recommended)
Set these environment variables in your deployment platform:

```bash
# Email and Reset URLs
EMAIL_VERIFICATION_URL_BASE=https://rsyatra.com/verify-email
PASSWORD_RESET_URL_BASE=https://rsyatra.com/reset-password
FRONTEND_LOGIN_URL=https://rsyatra.com/login

# Security (IMPORTANT!)
JWT_SECRET_KEY=your-secure-random-key-here
DB_PASSWORD=your-secure-db-password

# Email Configuration
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_FROM=your-email@gmail.com
```

### Option 2: Update Default Values (Done)
I've updated the default values in `config.py` to use production URLs:
- `email_verification_url_base`: `https://rsyatra.com/verify-email`
- `password_reset_url_base`: `https://rsyatra.com/reset-password`
- `frontend_login_url`: `https://rsyatra.com/login`

## Deployment Platform Instructions

### For Render.com
1. Go to your service dashboard
2. Click "Environment" tab
3. Add the environment variables above

### For Railway.app
1. Go to your project
2. Click "Variables" tab
3. Add the environment variables above

### For Docker
Add to your `docker-compose.yml`:
```yaml
environment:
  - EMAIL_VERIFICATION_URL_BASE=https://rsyatra.com/verify-email
  - PASSWORD_RESET_URL_BASE=https://rsyatra.com/reset-password
  - FRONTEND_LOGIN_URL=https://rsyatra.com/login
  - JWT_SECRET_KEY=your-secure-key
```

### For Heroku
```bash
heroku config:set EMAIL_VERIFICATION_URL_BASE=https://rsyatra.com/verify-email
heroku config:set PASSWORD_RESET_URL_BASE=https://rsyatra.com/reset-password
heroku config:set FRONTEND_LOGIN_URL=https://rsyatra.com/login
```

## Verification
After deployment, check the email content to ensure URLs point to:
- ✅ `https://rsyatra.com/verify-email?token=...`
- ❌ `http://localhost:3000/verify-email?token=...`

## Security Notes
1. **Never commit** sensitive environment variables to git
2. Use **secure random keys** for JWT_SECRET_KEY (generate with `openssl rand -hex 32`)
3. Use **app passwords** for Gmail SMTP, not your regular password
4. Keep different configurations for development/staging/production

## Testing
1. Create a test account
2. Check the verification email
3. Confirm the URL points to your production domain
4. Test the verification flow end-to-end
