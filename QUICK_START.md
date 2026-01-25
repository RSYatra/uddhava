# 🚀 Quick Start Guide - RSYatra Deployment

## Current Status
✅ **Backend**: Ready to deploy on Render  
✅ **Frontend**: Ready to deploy on Render  
✅ **Database**: Remote MySQL configured  
✅ **Security**: Audit completed, production-ready  
✅ **Code**: Pushed to GitHub testing branch  

---

## Next Steps (In Order)

### 1️⃣ Deploy Backend API
```
1. Go to https://dashboard.render.com
2. Click "New" → "Web Service"
3. Select "RSYatra/uddhava" repository
4. Set Configuration:
   - Name: rsyatra-api
   - Branch: testing
   - Build: pip install -r requirements.txt
   - Start: gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
5. Add Environment Variables (see CRITICAL VARS below)
6. Deploy!
```

### 2️⃣ Deploy Frontend
```
1. Go to https://dashboard.render.com
2. Click "New" → "Web Service"
3. Select "RSYatra/rsyatra.web-ui" repository
4. Set Configuration:
   - Name: rsyatra-frontend
   - Branch: testing
   - Root Dir: react-app
   - Build: npm install && npm run build
   - Start: npm run preview
5. Add Environment Variables:
   - NODE_ENV = production
   - VITE_API_URL = https://<backend-url>/api/v1
6. Deploy!
```

---

## 🔐 CRITICAL - Environment Variables

### Backend (Must Set on Render)
```
ENVIRONMENT = production
DEBUG = false
DB_HOST = srv1152.hstgr.io
DB_PORT = 3306
DB_USER = <from Hostinger>
DB_PASSWORD = <from Hostinger>
DB_NAME = <from Hostinger>
JWT_SECRET_KEY = <generate: openssl rand -hex 32>
JWT_ALGORITHM = HS256
SMTP_HOST = smtp.hostinger.com
SMTP_PORT = 587
SMTP_USER = <your-email@domain.com>
SMTP_PASSWORD = <your-smtp-password>
SMTP_FROM_EMAIL = <your-email@domain.com>
FRONTEND_URL = https://<frontend-domain>
CORS_ORIGINS = https://<frontend-domain>
```

### Frontend (Must Set on Render)
```
NODE_ENV = production
VITE_API_URL = https://<backend-url>/api/v1
```

---

## ✅ Testing After Deployment

### 1. Test Backend
```bash
# Health check
curl https://<backend-url>/api/v1/health

# Signup
curl -X POST https://<backend-url>/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test@123456","legal_name":"Test"}'
```

### 2. Test Frontend
- Visit: `https://<frontend-url>/signup`
- Try signing up with email
- Check inbox for verification email
- Verify email and login

---

## 📊 Current Git Status

**Backend (uddhava)**
- Branch: testing
- Latest: 954217a - "docs: Add comprehensive Render deployment guide"
- Ready for deployment ✅

**Frontend (rsyatra.web-ui)**
- Branch: testing
- Latest: 21c26d3 - "fix: Add build scripts and Render deployment configuration"
- Ready for deployment ✅

---

## 🐛 If Deployment Fails

### Frontend Build Fails
- Check: `render.yaml` has `rootDir: react-app`
- Check: Root `package.json` has build scripts
- Fix: `npm run build` works locally

### Backend Won't Start
- Check: All environment variables are set
- Check: Database is accessible
- Check: Render logs for startup errors

### Email Not Sending
- Check: SMTP credentials are correct
- Check: Hostinger allows SMTP connections
- Check: Email is valid (no typos)

### CORS Errors
- Check: VITE_API_URL in frontend matches backend URL
- Check: Backend has frontend URL in CORS_ORIGINS

---

## 📚 Full Documentation

See complete guides:
- `DEPLOYMENT_GUIDE.md` - Detailed deployment instructions
- `API_ENDPOINTS.md` - API reference
- `SECURITY_AUDIT_REPORT.md` - Security details

---

## 💡 Important Notes

1. **Credentials**: All kept in environment variables, NOT in git ✅
2. **HTTPS**: Automatic on Render, enabled ✅
3. **Database**: Remote MySQL, production-grade ✅
4. **Email**: Hostinger SMTP, configured ✅
5. **Rate Limiting**: Enabled on all endpoints ✅
6. **JWT**: 24-hour expiration, secure hashing ✅

---

## 🎯 Success Criteria

You'll know it's working when:
- ✅ Both services show "Live" on Render dashboard
- ✅ Frontend loads at its URL
- ✅ Signup form submits without errors
- ✅ Email verification link arrives
- ✅ Can verify email and login
- ✅ User appears in database

---

**Ready to deploy? Follow the steps above! 🚀**

For detailed help, see DEPLOYMENT_GUIDE.md
