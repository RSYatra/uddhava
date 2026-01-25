# RSYatra Deployment Guide

## Overview

This guide covers deploying both the frontend and backend for the RSYatra application on Render.

---

## 🚀 Frontend Deployment (Render)

### Prerequisites
- GitHub repository with code pushed to `testing` branch
- Render account (render.com)
- Environment variables configured

### Deployment Steps

1. **Connect GitHub Repository**
   - Go to [Render Dashboard](https://dashboard.render.com)
   - Click "New" → "Web Service"
   - Select "Build and deploy from a Git repository"
   - Connect your GitHub account
   - Select `RSYatra/rsyatra.web-ui` repository
   - Select `testing` branch

2. **Configure Service**
   - **Name**: `rsyatra-frontend`
   - **Root Directory**: `react-app` (important!)
   - **Build Command**: `npm install && npm run build`
   - **Start Command**: `npm run preview`
   - **Instance Type**: Free (or upgrade as needed)

3. **Set Environment Variables**
   - Go to "Environment" tab
   - Add the following variables:
     ```
     NODE_ENV = production
     VITE_API_URL = https://<your-api-domain>/api/v1
     ```

4. **Deploy**
   - Click "Create Web Service"
   - Render will automatically build and deploy
   - Your frontend will be available at: `https://<service-name>.onrender.com`

### Post-Deployment

- Test signup form: `https://<service-name>.onrender.com/signup`
- Test login: `https://<service-name>.onrender.com/login`
- Verify email notifications are received
- Check browser console for API errors

---

## 🔧 Backend Deployment (Render)

### Prerequisites
- GitHub repository with code pushed to `testing` branch
- Render account
- Database credentials from Hostinger
- SMTP credentials configured

### Deployment Steps

1. **Connect GitHub Repository**
   - Go to [Render Dashboard](https://dashboard.render.com)
   - Click "New" → "Web Service"
   - Select `RSYatra/uddhava` repository
   - Select `testing` branch

2. **Configure Service**
   - **Name**: `rsyatra-api`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`
   - **Instance Type**: Free (or upgrade as needed)

3. **Set Environment Variables** (CRITICAL)
   ```
   ENVIRONMENT = production
   DEBUG = false
   
   # Database
   DB_HOST = srv1152.hstgr.io
   DB_PORT = 3306
   DB_USER = <your-db-user>
   DB_PASSWORD = <your-db-password>
   DB_NAME = <your-db-name>
   
   # JWT
   JWT_SECRET_KEY = <generate-with: openssl rand -hex 32>
   JWT_ALGORITHM = HS256
   JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 1440
   
   # SMTP (Hostinger)
   SMTP_HOST = smtp.hostinger.com
   SMTP_PORT = 587
   SMTP_USER = <your-email@domain.com>
   SMTP_PASSWORD = <your-smtp-password>
   SMTP_FROM_EMAIL = <your-email@domain.com>
   
   # Frontend
   FRONTEND_URL = https://<frontend-domain>
   CORS_ORIGINS = https://<frontend-domain>,https://rsyatra.com
   ```

4. **Deploy**
   - Click "Create Web Service"
   - Render builds and deploys the API
   - API will be available at: `https://<service-name>.onrender.com`

### Post-Deployment

- Test health endpoint: `GET https://<service-name>.onrender.com/api/v1/health`
- Test signup: `POST https://<service-name>.onrender.com/api/v1/auth/signup`
- Verify email sending
- Check Render logs for errors

---

## 📋 Environment Variables Reference

### Frontend (.env in react-app)
```
VITE_API_URL=https://api.rsyatra.com/api/v1
VITE_API_VERSION=v1
VITE_APP_NAME=RSYatra
VITE_APP_ENV=production
```

### Backend (.env in uddhava root)
```
# Environment
ENVIRONMENT=production
DEBUG=false
PORT=10000

# Database
DB_HOST=srv1152.hstgr.io
DB_PORT=3306
DB_USER=username
DB_PASSWORD=password
DB_NAME=database_name

# JWT
JWT_SECRET_KEY=<strong-random-key>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440

# SMTP
SMTP_HOST=smtp.hostinger.com
SMTP_PORT=587
SMTP_USER=email@example.com
SMTP_PASSWORD=smtp_password
SMTP_FROM_EMAIL=email@example.com

# CORS
FRONTEND_URL=https://frontend.onrender.com
CORS_ORIGINS=https://frontend.onrender.com,https://rsyatra.com

# Security
ALLOWED_ORIGINS=https://frontend.onrender.com,https://rsyatra.com
ALLOWED_METHODS=GET,POST,PUT,DELETE,OPTIONS,PATCH
```

---

## 🔐 Security Checklist

Before deploying to production:

- [ ] Generate strong JWT secret: `openssl rand -hex 32`
- [ ] Use environment variables for ALL credentials
- [ ] Verify .env file is NOT in git
- [ ] Enable HTTPS/TLS (automatic on Render)
- [ ] Set ENVIRONMENT=production
- [ ] Set DEBUG=false
- [ ] Configure CORS for production domains
- [ ] Test email verification flow
- [ ] Test password reset flow
- [ ] Monitor error logs on Render
- [ ] Set up error alerts

---

## 🧪 Testing Deployment

### API Endpoints to Test

```bash
# Health check
curl https://api.rsyatra.com/api/v1/health

# Signup
curl -X POST https://api.rsyatra.com/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test@123456","legal_name":"Test"}'

# Login (should fail if email not verified)
curl -X POST https://api.rsyatra.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test@123456"}'
```

### Frontend Pages to Test

1. **Signup Page** (`/signup`)
   - Enter email, password, name
   - Verify validation works
   - Check verification email sent

2. **Email Verification** (`/verify-email?token=...`)
   - Verify email link works
   - Check user can login after verification

3. **Login Page** (`/login`)
   - Login with verified credentials
   - Check JWT token stored in localStorage
   - Check redirect to dashboard

4. **Forgot Password** (`/forgot-password`)
   - Enter email
   - Check reset email received
   - Reset password and login

---

## 🛠️ Troubleshooting

### Frontend Build Fails
**Error**: `Missing script: "build"`
**Solution**: 
- Verify `render.yaml` has `rootDir: react-app`
- Ensure `package.json` in root has build script
- Check `npm run build` works locally

### API Won't Start
**Error**: `Address already in use` or `Connection refused`
**Solution**:
- Check Render logs for startup errors
- Verify environment variables are set
- Ensure database is accessible
- Check SMTP credentials

### Email Not Sending
**Error**: `Failed to send verification email`
**Solution**:
- Verify SMTP credentials in Render environment
- Check SMTP_HOST and SMTP_PORT are correct
- Verify email account allows SMTP connections
- Check Render logs for SMTP errors

### CORS Errors
**Error**: `Access to XMLHttpRequest blocked by CORS policy`
**Solution**:
- Add frontend URL to CORS_ORIGINS in backend
- Verify FRONTEND_URL environment variable
- Check browser developer console for actual URL being used

---

## 📞 Support

For issues:
1. Check Render logs: Dashboard → Service → Logs
2. Check GitHub Issues
3. Review this guide
4. Contact support

---

## 📝 Production Checklist

- [ ] Both services deployed on Render
- [ ] Environment variables configured
- [ ] Database backups enabled
- [ ] Error monitoring/alerting set up
- [ ] Custom domain configured (if applicable)
- [ ] SSL certificate verified (auto on Render)
- [ ] Email sending tested
- [ ] End-to-end signup/login flow tested
- [ ] Rate limiting verified
- [ ] Security headers verified

---

**Deployment Status**: ✅ Ready to Deploy

For more information, see:
- [SECURITY_AUDIT_REPORT.md](./SECURITY_AUDIT_REPORT.md)
- [API_ENDPOINTS.md](./API_ENDPOINTS.md)
- [Render Deployment Docs](https://render.com/docs)
