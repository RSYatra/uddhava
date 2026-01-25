# Uddhava Repository Cleanup Summary

## Overview
The uddhava repository has been completely cleaned up and restructured to support only the minimal authentication backend needed for the RSYatra signup, login, and password reset functionality currently implemented in the frontend.

## What Was Removed

### Routes & APIs Deleted
- All yatra management endpoints (GET, POST, PUT, DELETE for yatras)
- All payment option endpoints
- All room category endpoints
- All center management endpoints
- All country code reference data endpoints
- All spiritual master reference data endpoints
- All yatra registration endpoints
- All devotee profile management endpoints (file uploads, complete profile, etc.)
- All administrative endpoints

### Database Models Removed
- `Yatra` - Yatra/pilgrimage model
- `YatraRegistration` - Registration for yatras
- `YatraMember` - Individual members in yatra registrations
- `RoomCategory` - Room categories per yatra
- `PaymentOption` - Payment methods
- `YatraPaymentOption` - Junction table for payments per yatra
- All related enums: `YatraStatus`, `RegistrationStatus`, `RoomPreference`, `PaymentMethod`, `PaymentStatus`, `MaritalStatus`, `InitiationStatus`

### Services Deleted
- `devotee_service.py` - Complex devotee profile management
- `gmail_service.py` - Gmail OAuth2 email service
- `yatra_service.py` - Yatra management service
- `yatra_registration_service.py` - Registration management
- `room_category_service.py` - Room category management
- `payment_option_service.py` - Payment option management
- `storage_service.py` - Google Cloud Storage service

### Schema Files Deleted
- All complex Pydantic schemas for yatra, payment, room, center, country code, spiritual master
- Complex devotee response schemas
- Email verification and password reset schemas

### Other Cleanup
- Removed `app/data/` directory with reference data (centers, country codes, spiritual masters)
- Removed `app/utils/` directory with yatra helper functions
- Deleted all old alembic migration files (kept only one clean initial migration)
- Deleted archived migration files in `alembic/versions_archive/`
- Deleted archived route files in `app/api/routes_archive/`
- Removed test scripts (`test_reference_apis.sh`)
- Removed legacy environment files (`uddhava.env`, `upload.env`)
- Removed Gmail and Google Cloud Storage dependencies from `requirements.txt`

## What Was Kept & Enhanced

### Core Database Models
- **Devotee** - Simplified to only essential authentication fields:
  - id, email (unique), password_hash, legal_name
  - email_verified, verification_token, verification_expires
  - password_reset_token, password_reset_expires
  - role (USER/ADMIN)
  - created_at, updated_at

- **FamilyMember** (NEW) - For future family management:
  - id, devotee_id (foreign key)
  - legal_name, date_of_birth, gender
  - mobile_number, email
  - relationship (spouse, child, parent, etc.)
  - created_at, updated_at

### API Endpoints (Minimal Set)
1. **Health Check**
   - `GET /api/v1/health` - Check API status and database connectivity

2. **Authentication Routes**
   - `POST /api/v1/auth/signup` - Register new account with email verification
   - `POST /api/v1/auth/verify-email` - Verify email from token
   - `POST /api/v1/auth/login` - Login and get JWT token
   - `POST /api/v1/auth/forgot-password` - Request password reset email
   - `POST /api/v1/auth/reset-password` - Reset password with token

### Email Service
- **SMTP Service** (NEW)
  - Replaces Gmail OAuth2 with direct SMTP connection
  - Configured for Hostinger SMTP (smtp.hostinger.com:587)
  - Uses TLS/STARTTLS encryption
  - Sends verification emails with 24-hour token expiry
  - Sends password reset emails with 1-hour token expiry

### Configuration
- Updated `app/core/config.py` with SMTP settings instead of Gmail
- SMTP credentials in environment variables:
  - SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM_EMAIL
  - FRONTEND_URL for email links

### Migrations
- Fresh initial migration: `001_initial.py`
  - Creates `devotees` table
  - Creates `family_members` table
  - Includes proper indexes and foreign keys
  - Can be rolled back cleanly

## Frontend Integration

The backend now supports the frontend authentication flow in `rsyatra.web-ui-1`:

1. **Signup Flow** (`/signup`)
   - Frontend: `POST /api/auth/signup` with legal_name, email, password
   - Backend: Creates unverified user, sends verification email
   - Email contains verification link with token
   - User clicks link to verify email

2. **Email Verification** (`/verify-email`)
   - Frontend: User receives email with verification link
   - Link contains verification token
   - Backend verifies token and marks email as verified

3. **Login Flow** (`/login`)
   - Frontend: `POST /api/auth/login` with email, password
   - Backend: Validates credentials, checks email verification, returns JWT
   - JWT used for authenticated requests

4. **Forgot Password Flow** (`/forgot-password`)
   - Frontend: `POST /api/auth/forgot-password` with email
   - Backend: Generates reset token, sends password reset email
   - User clicks link with token to reset password

## Next Steps for Development

### For Adding Family Member Management
1. The `FamilyMember` model is ready but endpoints are not yet implemented
2. Create new route file `app/api/routes/family.py`
3. Create service `app/services/family_service.py` if needed
4. Implement endpoints for managing family members (CRUD operations)

### For Event Registration
When implementing event registration later:
1. Create `Event` model (simpler than Yatra)
2. Create `EventRegistration` model
3. Support registering account holder and family members
4. Keep payment/room logic separate if needed

### Database Connection
Current setup uses MySQL. Update `.env` with your database:
```
DB_HOST=your_host
DB_PORT=3306
DB_USER=your_user
DB_PASSWORD=your_password
DB_NAME=your_database
```

### SMTP Configuration
Email settings are configured for Hostinger. Update `.env`:
```
SMTP_HOST=smtp.hostinger.com
SMTP_PORT=587
SMTP_USER=info@rsyatra.com
SMTP_PASSWORD=Devotee@108
SMTP_FROM_EMAIL=info@rsyatra.com
```

## Tested Compatibility

- ✅ Frontend signup form sends to `/api/auth/signup`
- ✅ Frontend login form sends to `/api/auth/login`
- ✅ Frontend forgot password sends to `/api/auth/forgot-password`
- ✅ JWT token generation and usage
- ✅ Email verification with token
- ✅ Password reset with token
- ✅ SMTP email sending (Hostinger)

## File Statistics

- **Lines deleted**: ~13,996
- **Lines added**: ~867
- **Files deleted**: 76
- **Files created**: 3 (auth.py, smtp_service.py, 001_initial.py migration)
- **Final codebase size**: ~500 lines of production code

## Branch Status
- All changes committed to `testing` branch
- No changes to main/master branch
- Ready for feature development
