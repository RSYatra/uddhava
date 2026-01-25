# RSYatra Backend API Endpoints

## Base URL
- Development: `http://localhost:8000`
- Production: `https://api.rsyatra.com` (or your deployed URL)

## Available Endpoints

### Health Check
```
GET /api/v1/health
```
Check API and database connectivity status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-01-25T23:00:00Z",
  "version": "1.0.0"
}
```

---

### Authentication Endpoints

#### 1. Signup
```
POST /api/v1/auth/signup
```

Register a new user account.

**Request:**
```json
{
  "legal_name": "Radha Krishna",
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Requirements:**
- Password: 8-128 characters, must contain uppercase, lowercase, digit, and special character
- Email: Valid email format
- Legal Name: Non-empty, max 127 characters

**Response (Success - 200):**
```json
{
  "success": true,
  "message": "Registration successful. Please check your email to verify your account.",
  "data": {
    "user_id": 1,
    "email": "user@example.com"
  }
}
```

**Response (Email Exists - 409):**
```json
{
  "success": false,
  "message": "Email already registered. Please login instead."
}
```

---

#### 2. Verify Email
```
POST /api/v1/auth/verify-email
```

Verify email address using token from verification email.

**Request:**
```json
{
  "token": "verification_token_from_email"
}
```

**Response (Success - 200):**
```json
{
  "success": true,
  "message": "Email verified successfully. You can now login.",
  "data": null
}
```

---

#### 3. Login
```
POST /api/v1/auth/login
```

Login with email and password to get JWT token.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response (Success - 200):**
```json
{
  "success": true,
  "message": "Login successful.",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "user": {
      "id": 1,
      "email": "user@example.com",
      "legal_name": "Radha Krishna"
    }
  }
}
```

**Response (Invalid Credentials - 401):**
```json
{
  "success": false,
  "message": "Invalid email or password."
}
```

**Response (Email Not Verified - 403):**
```json
{
  "success": false,
  "message": "Email not verified. Please check your email for verification link."
}
```

---

#### 4. Forgot Password
```
POST /api/v1/auth/forgot-password
```

Request password reset email. Always returns success for security.

**Request:**
```json
{
  "email": "user@example.com"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "If an account exists with this email, a password reset link has been sent.",
  "data": null
}
```

---

#### 5. Reset Password
```
POST /api/v1/auth/reset-password
```

Reset password using token from reset email.

**Request:**
```json
{
  "token": "reset_token_from_email",
  "password": "NewSecurePass123!"
}
```

**Response (Success - 200):**
```json
{
  "success": true,
  "message": "Password reset successful. You can now login with your new password.",
  "data": null
}
```

**Response (Invalid/Expired Token - 400):**
```json
{
  "success": false,
  "message": "Invalid or expired reset token."
}
```

---

## Authentication

Protected endpoints (future) require JWT token in Authorization header:

```
Authorization: Bearer <access_token>
```

---

## Error Responses

### 400 Bad Request
```json
{
  "success": false,
  "message": "Error description",
  "data": null
}
```

### 401 Unauthorized
Invalid or missing authentication token.

### 403 Forbidden
User not authorized for this action.

### 409 Conflict
Resource already exists.

### 422 Validation Error
Request validation failed.

### 429 Too Many Requests
Rate limit exceeded.

### 500 Internal Server Error
Server-side error occurred.

---

## Password Requirements

Passwords must:
- Be 8-128 characters long
- Contain at least one uppercase letter (A-Z)
- Contain at least one lowercase letter (a-z)
- Contain at least one digit (0-9)
- Contain at least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)

Example valid password: `MyPassword123!`

---

## Email Verification

After signup:
1. User receives verification email with a unique link
2. Link contains token and expires in 24 hours
3. User clicks link to verify email
4. User can login only after email verification

---

## Password Reset Flow

1. User requests reset via `/forgot-password`
2. If email exists, reset email is sent (not revealed for security)
3. User clicks reset link in email (valid for 1 hour)
4. User enters new password
5. Password is updated
6. User can login with new password

---

## Rate Limiting

Currently, rate limiting is disabled in development. In production:
- Signup: 3 attempts per 15 minutes per IP
- Login: 5 attempts per 15 minutes per IP

---

## CORS

Allowed origins configured in `main.py`:
- `http://localhost:5173` (Local Vite frontend)
- `https://rsyatra.com` (Production frontend)
- Add more as needed

---

## Environment Variables

Required:
```
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=changeme
DB_NAME=uddhava_db
JWT_SECRET_KEY=your-secret-key-change-in-production
SMTP_HOST=smtp.hostinger.com
SMTP_PORT=587
SMTP_USER=info@rsyatra.com
SMTP_PASSWORD=Devotee@108
SMTP_FROM_EMAIL=info@rsyatra.com
FRONTEND_URL=http://localhost:5173
```

---

## Documentation

API documentation available at:
- Swagger UI: `/docs`
- ReDoc: `/redoc`
- OpenAPI JSON: `/openapi.json`

(Only available in non-production environments)
