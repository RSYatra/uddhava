# Gmail SMTP on Render - Complete Fix Guide

## Problem: .env Works Locally But Not on Render

### Why This Happens:

```
LOCAL:
├── Reads .env file ✅
├── All MAIL_ variables loaded ✅
└── Connects from your home IP ✅

RENDER:
├── .env file NOT deployed (in .gitignore) ❌
├── Must set environment variables manually ❌
└── Connects from data center IP (Gmail suspicious) ❌
```

**Key Point:** `.env` file is intentionally NOT deployed to production (security best practice). You must manually set environment variables in Render Dashboard.

---

## Step-by-Step Fix for Gmail on Render

### OPTION 1: Quick Diagnostic Test (Recommended First)

This will tell you if Render blocks Gmail or if it's a configuration issue.

#### Step 1: Add Diagnostic Scripts to Repo

```bash
# Already created for you!
git add test_smtp_connection.py test_render_smtp.sh
git commit -m "Add SMTP diagnostic tools"
git push origin main
```

#### Step 2: SSH into Render and Run Test

```bash
# In Render Dashboard:
# 1. Go to your service
# 2. Click "Shell" tab
# 3. Run:
bash test_render_smtp.sh
```

**This will show you EXACTLY what's wrong!**

Results will tell you:
- ✅ Port 587 works → Credentials problem, fix below
- ✅ Port 465 works → Use SSL instead of STARTTLS
- ❌ All ports blocked → Render blocks Gmail, must use SendGrid

---

### OPTION 2: Fix Gmail Configuration (If Ports Work)

#### Step 1: Generate Gmail App Password

**IMPORTANT:** You MUST use App Password, not your regular Gmail password!

1. Go to: https://myaccount.google.com/security
2. Enable "2-Step Verification" (required for App Passwords)
3. After 2FA is enabled:
   - Go back to Security
   - Scroll down to "2-Step Verification"
   - Click "App passwords"
4. Generate new app password:
   - App: Mail
   - Device: Other → "Render Uddhava API"
5. Click "Generate"
6. Copy the 16-character password (format: `xxxx xxxx xxxx xxxx`)
7. **Remove all spaces:** `xxxxxxxxxxxxxxxx`

#### Step 2: Set ALL Environment Variables in Render

**CRITICAL:** You must set EVERY variable. Missing even one = failure.

Go to: Render Dashboard → uddhava-api → Environment → Add Environment Variable

```bash
# 1. Gmail Credentials
MAIL_USERNAME=kumartiwariprashant@gmail.com
MAIL_PASSWORD=<your-16-char-app-password-no-spaces>
MAIL_FROM=kumartiwariprashant@gmail.com

# 2. Server Configuration (Port 587 - STARTTLS)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_STARTTLS=true
MAIL_SSL_TLS=false

# 3. Authentication
MAIL_USE_CREDENTIALS=true
MAIL_VALIDATE_CERTS=true
```

**IMPORTANT NOTES:**
- `MAIL_PASSWORD` must be the App Password (16 chars, no spaces)
- NOT your regular Gmail password
- Values are case-sensitive: `true` not `True`

#### Step 3: Verify Environment Variables Are Set

After adding all variables:
1. Click "Save Changes"
2. Render will redeploy automatically
3. Go to Shell tab and verify:

```bash
echo $MAIL_SERVER
echo $MAIL_PORT
echo $MAIL_USERNAME
# Don't echo MAIL_PASSWORD for security
```

If any shows empty, it's not set correctly!

---

### OPTION 3: Try Port 465 (SSL) Instead of 587 (STARTTLS)

Some cloud providers block port 587 but allow 465.

#### Render Environment Variables (Port 465 - SSL):

```bash
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=465
MAIL_STARTTLS=false
MAIL_SSL_TLS=true
MAIL_USERNAME=kumartiwariprashant@gmail.com
MAIL_PASSWORD=<your-app-password>
MAIL_FROM=kumartiwariprashant@gmail.com
MAIL_USE_CREDENTIALS=true
MAIL_VALIDATE_CERTS=true
```

**Key changes:**
- Port changed to 465
- `MAIL_STARTTLS=false`
- `MAIL_SSL_TLS=true`

---

## Common Issues & Solutions

### Issue 1: "I uploaded my .env file but it still doesn't work"

**Problem:** `.env` files are in `.gitignore` and never deployed to production (security).

**Solution:** Must manually set each variable in Render Dashboard.

**How to check .env is in .gitignore:**
```bash
cat .gitignore | grep .env
# Should show: .env
```

---

### Issue 2: "Timeout connecting to smtp.gmail.com"

**Possible Causes:**

**A) Port is blocked by Render**
- Test: Run diagnostic script (Option 1)
- Solution: Use SendGrid or port 465

**B) Missing environment variables**
- Test: SSH into Render, run `env | grep MAIL_`
- Solution: Add all 9 MAIL_ variables

**C) Gmail blocking Render's IP**
- Test: Generate App Password and use it
- Solution: Use App Password (not regular password)

---

### Issue 3: "SMTPAuthenticationError"

**Problem:** Credentials are wrong or not using App Password.

**Solution:**
1. ✅ Generate Gmail App Password (not regular password)
2. ✅ Remove all spaces from App Password
3. ✅ Use your Gmail address for MAIL_USERNAME (not "apikey")
4. ✅ Verify MAIL_FROM matches MAIL_USERNAME

---

### Issue 4: "Variables are set but still timeout"

**Problem:** Render might block Gmail SMTP completely.

**Check with diagnostic:**
```bash
# In Render Shell:
python3 test_smtp_connection.py
```

If all ports timeout → **Render blocks Gmail SMTP**

**Solution:** Must use email service designed for servers:
- SendGrid (100 emails/day free)
- Mailgun (5,000 emails/month free)
- AWS SES (cheapest for high volume)

---

## How to Verify Environment Variables Are Actually Set

### Method 1: Render Dashboard
1. Go to Environment tab
2. Check all MAIL_ variables are listed
3. Values should NOT be empty

### Method 2: Render Shell
```bash
# SSH into Render
env | grep MAIL_

# Should show:
MAIL_USERNAME=kumartiwariprashant@gmail.com
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_FROM=kumartiwariprashant@gmail.com
MAIL_STARTTLS=true
MAIL_SSL_TLS=false
MAIL_USE_CREDENTIALS=true
MAIL_VALIDATE_CERTS=true
# MAIL_PASSWORD won't show (hidden)
```

### Method 3: Check Logs
```bash
# Your enhanced logging shows:
[INFO] Email service configured: smtp.gmail.com:587 (STARTTLS=True, SSL=False)
```

If this message appears → Configuration loaded ✅
If missing → Variables not set ❌

---

## Whitelist Options (If Render Blocks Gmail)

### Option A: Contact Render Support

**Render doesn't publicly document SMTP port restrictions.**

1. Go to: https://render.com/docs/support
2. Submit ticket: "Request Gmail SMTP access for service"
3. Provide:
   - Service name: uddhava-api
   - Reason: User email verification
   - Ports needed: 587 and/or 465

**Response time:** 1-3 business days
**Success rate:** Unknown (Render may not allow it)

### Option B: Use Render's SMTP Relay (If Available)

Check Render docs: https://render.com/docs

Some platforms offer SMTP relay services, but Render doesn't publicly document this.

### Option C: Use Gmail via OAuth2 (Advanced)

Instead of App Password, use OAuth2 tokens. This is more complex but might work better.

**Requirements:**
- Google Cloud Project
- OAuth2 credentials
- Token refresh logic

**Not recommended** unless you have experience with OAuth2.

---

## Decision Tree: What Should I Do?

```
Start Here: Did you set environment variables in Render Dashboard?
│
├─ NO → Set all 9 MAIL_ variables → Test again
│
└─ YES → Run diagnostic script (test_render_smtp.sh)
    │
    ├─ Port 587 works?
    │   └─ YES → Check App Password is correct
    │       └─ Still fails? → Try port 465
    │
    ├─ Port 465 works?
    │   └─ YES → Change to SSL config (port 465)
    │
    └─ All ports blocked?
        └─ YES → Must use SendGrid/Mailgun/AWS SES
```

---

## Testing Checklist

Before deploying, verify:

- [ ] Generated Gmail App Password (not regular password)
- [ ] Removed all spaces from App Password
- [ ] Set all 9 MAIL_ variables in Render Dashboard
- [ ] Used correct values: `true` not `True`
- [ ] MAIL_USERNAME is your Gmail address
- [ ] MAIL_FROM is your Gmail address
- [ ] Deployed test scripts to diagnose
- [ ] Ran diagnostic script in Render Shell

---

## Expected Timeline

### If Gmail Works on Render:
1. Generate App Password: 5 minutes
2. Set environment variables: 5 minutes
3. Render redeploy: 2-3 minutes
4. Test: 1 minute
**Total: ~15 minutes**

### If Gmail is Blocked:
1. Sign up for SendGrid: 5 minutes
2. Get API key: 2 minutes
3. Verify sender: 3 minutes
4. Update Render config: 2 minutes
5. Render redeploy: 2-3 minutes
**Total: ~15 minutes**

---

## Quick Commands

### Deploy Diagnostic Tools:
```bash
git add test_smtp_connection.py test_render_smtp.sh GMAIL_RENDER_FIX.md
git commit -m "Add Gmail SMTP diagnostic tools"
git push origin main
```

### Test in Render Shell:
```bash
# After deployment, in Render Shell:
bash test_render_smtp.sh
```

### Check Environment Variables:
```bash
# In Render Shell:
env | grep MAIL_ | sort
```

---

## Support Resources

- Render Support: https://render.com/docs/support
- Gmail App Passwords: https://support.google.com/accounts/answer/185833
- SendGrid Docs: https://docs.sendgrid.com/for-developers/sending-email/getting-started-smtp

---

**Next Step:** Run the diagnostic script to see if Render blocks Gmail SMTP!
