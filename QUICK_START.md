# 🚀 Quick Start Guide - Testing SNAPPY Auth

## Run All Tests (Easiest!)

```cmd
powershell -ExecutionPolicy Bypass -File test_api_simple.ps1
```

This single command will:
- ✅ Generate 3 product keys
- ✅ Validate a key
- ✅ Register a test user
- ✅ Login the user
- ✅ Get current user details
- ✅ Complete onboarding with firm details

---

## Single Command Tests (Windows CMD)

### 1️⃣ Generate Keys
```cmd
curl -X POST http://localhost:5000/api/admin/keys/generate -H "Content-Type: application/json" -d "{\"count\": 3, \"days\": 365}"
```

### 2️⃣ Validate Key
```cmd
curl -X POST http://localhost:5000/api/auth/validate-key -H "Content-Type: application/json" -d "{\"key\": \"SNAPPY-XXXXXXXXXXXXXXXX\"}"
```

### 3️⃣ Register User
```cmd
curl -X POST http://localhost:5000/api/auth/register -H "Content-Type: application/json" -d "{\"email\": \"user@example.com\", \"password\": \"pass123\", \"product_key\": \"SNAPPY-XXX\"}"
```

### 4️⃣ Login
```cmd
curl -X POST http://localhost:5000/api/auth/login -H "Content-Type: application/json" -c cookies.txt -d "{\"email\": \"user@example.com\", \"password\": \"pass123\"}"
```

### 5️⃣ Get Current User
```cmd
curl -X GET http://localhost:5000/api/auth/me -b cookies.txt
```

### 6️⃣ Complete Onboarding
```cmd
curl -X POST http://localhost:5000/api/auth/onboard -H "Content-Type: application/json" -b cookies.txt -d "{\"firm_name\": \"My Law Firm\", \"firm_address\": \"123 Street\", \"default_template\": \"LAW_001\", \"invoice_prefix\": \"LAW\", \"default_tax_rate\": 18.0, \"currency\": \"INR\"}"
```

---

## PowerShell One-Liners

### Generate Keys
```powershell
Invoke-RestMethod -Uri "http://localhost:5000/api/admin/keys/generate" -Method POST -ContentType "application/json" -Body '{"count":5,"days":365}'
```

### Login with Session
```powershell
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
Invoke-RestMethod -Uri "http://localhost:5000/api/auth/login" -Method POST -ContentType "application/json" -Body '{"email":"test@example.com","password":"testpass123"}' -SessionVariable session
```

### Get User
```powershell
Invoke-RestMethod -Uri "http://localhost:5000/api/auth/me" -Method GET -WebSession $session
```

---

## Expected Output Examples

### ✅ Key Generation Success
```json
{
  "message": "3 product keys generated",
  "keys": [
    "SNAPPY-093A2E6A045CDE35",
    "SNAPPY-2F408C004EE35BFF",
    "SNAPPY-BCFCDE90E76048F9"
  ]
}
```

### ✅ Login Success
```json
{
  "message": "Login successful",
  "user": {
    "id": 1,
    "email": "test@example.com",
    "is_onboarded": true
  }
}
```

### ✅ Onboarding Success
```json
{
  "message": "Onboarding completed successfully",
  "firm": {
    "firm_name": "Test Law Firm",
    "default_template": "LAW_001",
    "invoice_prefix": "TEST"
  }
}
```

---

## Troubleshooting

### Issue: "Bad Request - Failed to decode JSON"
**Windows CMD:** Use `\"` to escape quotes inside JSON string

### Issue: "Port number was not a decimal"
**Cause:** Line breaks in curl command  
**Fix:** Put entire command on one line

### Issue: "cannot use a string pattern on a bytes-like object"
**Status:** ✅ FIXED in backend (SESSION_USE_SIGNER=False)

---

## Files Created

- ✅ `test_api_simple.ps1` - Automated test script (RECOMMENDED)
- ✅ `test_auth_api.bat` - Windows batch script
- ✅ `test_auth_api.ps1` - Advanced PowerShell script
- ✅ `TEST_RESULTS.md` - Latest test results
- ✅ `NEW_FEATURES.md` - Complete documentation
- ✅ `QUICK_START.md` - This file!

---

## What's Working

✅ Product key generation  
✅ Product key validation  
✅ User registration  
✅ User login  
✅ Session management  
✅ Onboarding with firm details  
✅ Get current user  
✅ Firm settings update  
✅ Template selection (LAW_001 or Simple)

---

## What's Next (Frontend)

⏳ Login page UI  
⏳ Registration page UI  
⏳ Onboarding wizard (multi-step form)  
⏳ File upload (logo, signature, UPI QR)  
⏳ Settings pages  
⏳ Template selector in settings  
⏳ Auth guard for protected routes

---

🎉 **Backend is 100% ready for frontend integration!**
