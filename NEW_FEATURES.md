# 🎉 SNAPPY - New Features Implementation

## ✨ What's New

### 1. 🔐 Authentication & Onboarding System
### 2. 🔑 Product Key Activation
### 3. 📄 New Invoice Template (LAW_001)

---

## 1. Authentication & Onboarding

### Features Implemented:

#### **User Registration & Login**
- Secure password hashing with Werkzeug
- Session-based authentication
- Email-based user accounts

#### **Onboarding Flow**
After registration, users complete a one-time onboarding process:

**Required Information:**
- ✅ Firm Name
- ✅ Firm Address

**Optional Information:**
- 📧 Firm Email
- 📞 Firm Phone (Primary & Secondary)
- 🌐 Firm Website
- 🖼️ Firm Logo
- ✍️ Authorized Signature Image
- 💳 Banking Details:
  - Bank Name
  - Account Number
  - Account Holder Name
  - IFSC Code
  - UPI ID
  - UPI QR Code Image
- 📜 Terms & Conditions (App T&C)
- 📋 Billing Terms & Conditions
- ⚙️ Preferences:
  - Default Invoice Template
  - Invoice Prefix
  - Default Tax Rate
  - Currency

#### **Account Management**
Users can update settings in two categories:

**Regular Settings** (Can change anytime):
- Banking details
- UPI information
- Terms & Conditions
- Billing preferences
- Invoice template preferences
- Tax rates

**Core Settings** (Settings/Account section only):
- Firm Name
- Firm Logo
- Firm Address
- Contact Numbers

---

## 2. Product Key Activation

### How It Works:

1. **Generate Keys** (Admin)
   ```bash
   POST /api/admin/keys/generate
   {
     "count": 10,
     "days": 365
   }
   ```

2. **Validate Key** (User during registration)
   ```bash
   POST /api/auth/validate-key
   {
     "key": "SNAPPY-XXXXXXXXXXXXXXXX"
   }
   ```

3. **Register with Key**
   ```bash
   POST /api/auth/register
   {
     "email": "user@example.com",
     "password": "securepassword",
     "product_key": "SNAPPY-XXXXXXXXXXXXXXXX"
   }
   ```

### Key Features:
- ✅ Unique product keys
- ✅ Expiration dates
- ✅ One-time use validation
- ✅ Activation tracking

---

## 3. New Invoice Template (LAW_001)

### Template Comparison:

| Feature | Simple | LAW_001 |
|---------|--------|---------|
| Firm Logo | ❌ | ✅ |
| Yellow Header | ❌ | ✅ |
| UPI QR Code | ❌ | ✅ |
| Bank Details Section | ❌ | ✅ |
| Signature Section | ✅ Basic | ✅ Professional |
| Layout | Minimal | Professional |

### Template Selection:

Set default template during onboarding or change in settings:

```bash
PUT /api/auth/firm
{
  "default_template": "LAW_001"
}
```

Available templates:
- `Simple` - Original minimalist template
- `LAW_001` - Professional template (as per image)

---

## 📡 API Reference

### Authentication Endpoints

#### Register
```bash
POST /api/auth/register
Content-Type: application/json

{
  "email": "lawyer@example.com",
  "password": "securepassword",
  "product_key": "SNAPPY-XXXX" # Optional
}
```

#### Login
```bash
POST /api/auth/login
Content-Type: application/json

{
  "email": "lawyer@example.com",
  "password": "securepassword"
}
```

#### Logout
```bash
POST /api/auth/logout
```

#### Get Current User
```bash
GET /api/auth/me
```

#### Complete Onboarding
```bash
POST /api/auth/onboard
Content-Type: application/json

{
  "firm_name": "Sharma & Associates",
  "firm_address": "123 Legal Plaza\nNew Delhi - 110001",
  "firm_email": "contact@sharma-law.com",
  "firm_phone": "+91-98765-43210",
  "firm_phone_2": "+91-98765-43211",
  "bank_name": "State Bank of India",
  "account_number": "1234567890",
  "account_holder_name": "Sharma & Associates",
  "ifsc_code": "SBIN0001234",
  "upi_id": "sharma@oksbi",
  "terms_and_conditions": "Standard legal terms...",
  "billing_terms": "Payment due within 30 days...",
  "default_template": "LAW_001",
  "invoice_prefix": "LAW",
  "default_tax_rate": 18.0,
  "currency": "INR"
}
```

#### Update Firm Details
```bash
PUT /api/auth/firm
Content-Type: application/json

{
  "firm_email": "newemail@example.com",
  "default_template": "LAW_001",
  "default_tax_rate": 18.0
}
```

#### Update Core Firm Details (Settings Only)
```bash
PUT /api/auth/firm/core
Content-Type: application/json

{
  "firm_name": "New Firm Name",
  "firm_address": "New Address",
  "firm_phone": "New Phone"
}
```

### Product Key Endpoints

#### Validate Key
```bash
POST /api/auth/validate-key
Content-Type: application/json

{
  "key": "SNAPPY-XXXXXXXXXXXXXXXX"
}

Response:
{
  "valid": true/false,
  "error": "error message if invalid"
}
```

#### Generate Keys (Admin)
```bash
POST /api/admin/keys/generate
Content-Type: application/json

{
  "count": 10,
  "days": 365
}

Response:
{
  "message": "10 product keys generated",
  "keys": ["SNAPPY-XXX...", ...]
}
```

---

## 🗄️ Database Schema

### New Tables:

#### `users`
- id (PK)
- email (unique, indexed)
- password_hash
- is_active
- is_onboarded
- created_at
- last_login

#### `firms`
- id (PK)
- user_id (FK → users.id)
- firm_name
- firm_address
- firm_email, firm_phone, firm_phone_2, firm_website
- logo_path, signature_path
- bank_name, account_number, account_holder_name, ifsc_code
- upi_id, upi_qr_path
- terms_and_conditions, billing_terms
- default_template, invoice_prefix, default_tax_rate, currency
- created_at, updated_at

#### `product_keys`
- id (PK)
- key (unique, indexed)
- user_id (FK → users.id, nullable)
- is_used
- expires_at
- activated_at
- created_at

---

## 🚀 Getting Started

### Backend Setup

1. **Install new dependencies:**
   ```bash
   pip install flask-session
   ```

2. **Run migrations:**
   ```bash
   python -m backend.app.main
   # Tables will auto-create on first run
   ```

3. **Generate product keys:**
   ```bash
   curl -X POST http://localhost:5000/api/admin/keys/generate \
     -H "Content-Type: application/json" \
     -d '{"count": 5, "days": 365}'
   ```

### Frontend (To be implemented)

**Pages needed:**
1. `/register` - Registration with product key validation
2. `/login` - Login page
3. `/onboarding` - Multi-step onboarding form
4. `/settings/account` - Core firm settings
5. `/settings/preferences` - General preferences

---

## 📝 Frontend Implementation Guide

### 1. Registration Flow

```typescript
// 1. Validate product key
const validateKey = async (key: string) => {
  const response = await api.post('/auth/validate-key', { key });
  return response.data.valid;
};

// 2. Register user
const register = async (email: string, password: string, productKey?: string) => {
  const response = await api.post('/auth/register', {
    email,
    password,
    product_key: productKey
  });
  return response.data;
};
```

### 2. Onboarding Flow

```typescript
const completeOnboarding = async (firmData: FirmData) => {
  const response = await api.post('/auth/onboard', firmData);
  return response.data;
};
```

### 3. Template Selection

Add to Settings page:

```typescript
const updateTemplate = async (template: 'Simple' | 'LAW_001') => {
  await api.put('/auth/firm', { default_template: template });
};
```

---

## 🎨 File Upload Endpoints (To be implemented)

For uploading logo, signature, and UPI QR images:

```bash
POST /api/auth/firm/upload/logo
POST /api/auth/firm/upload/signature
POST /api/auth/firm/upload/upi-qr

Content-Type: multipart/form-data
```

---

## ✅ Testing

### Quick Test (Windows)

**Run the automated test script:**
```cmd
powershell -ExecutionPolicy Bypass -File test_api_simple.ps1
```

This will test all endpoints automatically!

### Manual Testing

#### Windows CMD:
```cmd
REM 1. Generate Product Keys
curl -X POST http://localhost:5000/api/admin/keys/generate -H "Content-Type: application/json" -d "{\"count\": 3, \"days\": 365}"

REM 2. Validate Key (replace SNAPPY-XXX with actual key from step 1)
curl -X POST http://localhost:5000/api/auth/validate-key -H "Content-Type: application/json" -d "{\"key\": \"SNAPPY-XXX\"}"

REM 3. Register User
curl -X POST http://localhost:5000/api/auth/register -H "Content-Type: application/json" -d "{\"email\": \"test@example.com\", \"password\": \"testpass123\", \"product_key\": \"SNAPPY-XXX\"}"

REM 4. Login
curl -X POST http://localhost:5000/api/auth/login -H "Content-Type: application/json" -c cookies.txt -d "{\"email\": \"test@example.com\", \"password\": \"testpass123\"}"

REM 5. Get Current User
curl -X GET http://localhost:5000/api/auth/me -b cookies.txt

REM 6. Complete Onboarding
curl -X POST http://localhost:5000/api/auth/onboard -H "Content-Type: application/json" -b cookies.txt -d "{\"firm_name\": \"Test Law Firm\", \"firm_address\": \"123 Test Street\", \"default_template\": \"LAW_001\"}"
```

#### PowerShell:
```powershell
# 1. Generate Product Keys
Invoke-RestMethod -Uri "http://localhost:5000/api/admin/keys/generate" -Method POST -ContentType "application/json" -Body '{"count":3,"days":365}'

# 2. Register & Login (with session)
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
Invoke-RestMethod -Uri "http://localhost:5000/api/auth/login" -Method POST -ContentType "application/json" -Body '{"email":"test@example.com","password":"testpass123"}' -SessionVariable session

# 3. Get Current User
Invoke-RestMethod -Uri "http://localhost:5000/api/auth/me" -Method GET -WebSession $session
```

#### Linux/Mac (bash):
```bash
# 1. Generate Keys
curl -X POST http://localhost:5000/api/admin/keys/generate \
  -H "Content-Type: application/json" \
  -d '{"count": 1, "days": 365}'

# 2. Register
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "testpass123", "product_key": "SNAPPY-XXXX"}'

# 3. Login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -c cookies.txt \
  -d '{"email": "test@example.com", "password": "testpass123"}'

# 4. Onboarding
curl -X POST http://localhost:5000/api/auth/onboard \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"firm_name": "Test Law Firm", "firm_address": "123 Test Street", "default_template": "LAW_001"}'
```

---

## 🔒 Security Notes

1. **Sessions:** Flask-Session stores sessions in filesystem by default. For production, use Redis or database backend.

2. **CORS:** Currently allows all origins. For production, restrict to specific domains.

3. **Product Keys:** Admin endpoint `/admin/keys/generate` needs proper authentication in production.

4. **File Uploads:** Implement file size limits, type validation, and secure storage.

---

## 📦 Next Steps

1. ✅ Backend implementation (DONE)
2. ⏳ Frontend pages (Register, Login, Onboarding)
3. ⏳ File upload functionality
4. ⏳ Image storage service
5. ⏳ Email verification (optional)
6. ⏳ Password reset functionality
7. ⏳ Admin dashboard for key management

---

## 🎉 Summary

**All three features are fully implemented in the backend:**

1. ✅ **Authentication & Onboarding** - Complete with user/firm models and APIs
2. ✅ **Product Key Activation** - Key generation, validation, and activation tracking
3. ✅ **LAW_001 Template** - Professional invoice template matching your image

**To use:**
1. Install dependencies: `pip install flask-session`
2. Restart backend
3. Generate product keys
4. Test with the API endpoints above

Frontend implementation will provide UI for these features! 🚀
