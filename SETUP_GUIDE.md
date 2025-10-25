# 🚀 SNAPPY Deployment Setup Guide

## ✅ Changes Made

### 1. **API Versioning Added**
All API endpoints now include `/v1/` prefix:
- Old: `http://localhost:5000/api/auth/login`
- New: `http://localhost:5000/api/v1/auth/login`

### 2. **Environment Configuration Updated**
Created comprehensive `.env` structure for all deployment scenarios.

### 3. **Supabase Database Schema Created**
Complete PostgreSQL schema with:
- Users & Firms tables
- Subscription management
- License keys (decoupled from main system)
- Cloud backup metadata
- Payment history
- Audit logging

---

## 📝 Setup Instructions

### **Step 1: Update Your Environment Variables**

Copy the example files and fill in your Supabase credentials:

```bash
# Backend
cp .env.example .env

# Frontend
cp frontend/.env.example frontend/.env
```

### **Step 2: Fill in Supabase Credentials**

Open `.env` and update these values:

```bash
# ====================================
# SUPABASE CONFIGURATION
# ====================================
# Get these from: https://app.supabase.com/project/_/settings/api

SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.YOUR_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.YOUR_SERVICE_ROLE_KEY
SUPABASE_JWT_SECRET=your-jwt-secret
```

**Where to find these:**
1. Go to https://app.supabase.com
2. Select your project
3. Click on "Settings" → "API"
4. Copy:
   - Project URL → `SUPABASE_URL`
   - `anon` `public` key → `SUPABASE_ANON_KEY`
   - `service_role` `secret` key → `SUPABASE_SERVICE_ROLE_KEY`
5. Go to "Settings" → "API" → "JWT Secret" → `SUPABASE_JWT_SECRET`

### **Step 3: Fill in Frontend Environment**

Open `frontend/.env` and update:

```bash
VITE_API_BASE_URL=http://localhost:5000/api/v1
VITE_SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.YOUR_ANON_KEY
```

### **Step 4: Set Up Supabase Database**

1. Go to https://app.supabase.com
2. Select your project
3. Click on "SQL Editor"
4. Click "New query"
5. Copy the entire content of `backend/supabase_schema.sql`
6. Paste and click "Run"

This will create:
- ✅ All tables (users, firms, subscriptions, license_keys, etc.)
- ✅ Indexes for performance
- ✅ Row Level Security (RLS) policies
- ✅ Triggers for auto-updating timestamps
- ✅ Views for convenience
- ✅ Default subscription plans

### **Step 5: Create Storage Buckets**

In Supabase Dashboard:

1. Go to "Storage"
2. Click "New bucket"

Create these 3 buckets:

**Bucket 1: `user-backups`**
- Name: `user-backups`
- Public: ❌ No (Private)
- Allowed MIME types: `application/octet-stream, application/x-sqlite3`
- Max file size: 100 MB

**Bucket 2: `user-uploads`**
- Name: `user-uploads`
- Public: ❌ No (Private)
- Allowed MIME types: `image/png, image/jpeg, image/jpg`
- Max file size: 5 MB

**Bucket 3: `invoice-pdfs` (Optional)**
- Name: `invoice-pdfs`
- Public: ❌ No (Private)
- Allowed MIME types: `application/pdf`
- Max file size: 10 MB

### **Step 6: Configure Storage Policies**

For each bucket, set up RLS policies:

```sql
-- user-backups policies
CREATE POLICY "Users can upload own backups"
ON storage.objects FOR INSERT
WITH CHECK (bucket_id = 'user-backups' AND auth.uid()::text = (storage.foldername(name))[1]);

CREATE POLICY "Users can download own backups"
ON storage.objects FOR SELECT
USING (bucket_id = 'user-backups' AND auth.uid()::text = (storage.foldername(name))[1]);

CREATE POLICY "Users can delete own backups"
ON storage.objects FOR DELETE
USING (bucket_id = 'user-backups' AND auth.uid()::text = (storage.foldername(name))[1]);

-- Similar policies for user-uploads
CREATE POLICY "Users can upload own files"
ON storage.objects FOR INSERT
WITH CHECK (bucket_id = 'user-uploads' AND auth.uid()::text = (storage.foldername(name))[1]);

CREATE POLICY "Users can view own files"
ON storage.objects FOR SELECT
USING (bucket_id = 'user-uploads' AND auth.uid()::text = (storage.foldername(name))[1]);
```

### **Step 7: Set Up Razorpay (Later)**

For now, just create test keys:

1. Go to https://dashboard.razorpay.com/signup
2. Create account
3. Go to Settings → API Keys
4. Generate Test Keys
5. Add to `.env`:

```bash
RAZORPAY_KEY_ID=rzp_test_your_test_key
RAZORPAY_KEY_SECRET=your_test_secret
```

---

## 🧪 Testing the Setup

### Test 1: Check API Versioning

```bash
# Start backend
cd backend
python -m flask run

# In another terminal, test new endpoints:
curl http://localhost:5000/api/v1
curl http://localhost:5000/health
```

Expected response:
```json
{
  "version": "v1",
  "app": "SNAPPY",
  "company": "Parth Nuwal",
  "endpoints": {...}
}
```

### Test 2: Check Frontend API Connection

```bash
# Start frontend
cd frontend
npm run dev
```

Open browser console and check for API calls to `/api/v1/auth/me`

---

## 📊 Database Verification

After running the schema, verify in Supabase:

```sql
-- Check tables created
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

-- Check subscription plans
SELECT * FROM subscription_plans;

-- Should see 4 plans: trial, starter, pro, enterprise
```

---

## 🔐 Product Key System (Separate)

The license key system is now **decoupled** and will work as follows:

### Flow:
```
1. User visits website (to be created)
   ↓
2. Selects plan (Starter/Pro/Enterprise)
   ↓
3. Pays via Razorpay
   ↓
4. Payment webhook triggers key generation
   ↓
5. Key inserted into Supabase `license_keys` table
   ↓
6. Email sent to user with key: SNAPPY-XXXX-XXXX-XXXX-XXXX
   ↓
7. User enters key in desktop app
   ↓
8. Desktop app validates key via API
   ↓
9. Key bound to device_id
   ↓
10. Desktop app can work offline for 7 days
```

**We'll build the payment website separately** with:
- Landing page
- Pricing page
- Checkout flow
- Razorpay integration
- Email sending (key delivery)
- Admin dashboard (manage keys)

---

## 📁 Updated File Structure

```
snappy/
├── .env (YOUR SUPABASE CREDS HERE)
├── .env.example (template with all vars)
├── frontend/
│   ├── .env (YOUR SUPABASE CREDS HERE)
│   ├── .env.example (template)
│   └── src/
│       └── api.ts (✅ Updated with v1 endpoints)
├── backend/
│   ├── supabase_schema.sql (✅ NEW - run in Supabase)
│   └── app/
│       └── main.py (✅ Updated with /api/v1 prefix)
└── docs/
    ├── DEPLOYMENT_PLAN.md
    ├── TODO_DEPLOYMENT.md
    ├── ARCHITECTURE.md
    └── SETUP_GUIDE.md (this file)
```

---

## ✅ Checklist

Before proceeding, make sure you've completed:

- [ ] Created `.env` file with Supabase credentials
- [ ] Created `frontend/.env` file with Supabase credentials
- [ ] Ran `supabase_schema.sql` in Supabase SQL Editor
- [ ] Verified 4 subscription plans exist in database
- [ ] Created 3 storage buckets (user-backups, user-uploads, invoice-pdfs)
- [ ] Set up storage RLS policies
- [ ] Tested new `/api/v1` endpoints
- [ ] Frontend connects to new API endpoints

---

## 🐛 Troubleshooting

### Issue: API returns 404

**Solution:** Make sure you're using `/api/v1/` in URLs, not `/api/`

### Issue: CORS errors in frontend

**Solution:** Check that `VITE_API_BASE_URL` in `frontend/.env` matches your backend URL

### Issue: Supabase connection fails

**Solution:** 
1. Verify credentials are correct
2. Check Supabase project is not paused
3. Ensure RLS policies are set up correctly

### Issue: Storage bucket access denied

**Solution:** Make sure storage RLS policies are created (Step 6)

---

## 🎯 Next Steps

Once setup is complete, we'll implement:

1. **JWT Authentication** (token-based for desktop app)
2. **Subscription API** (CRUD operations)
3. **License Validation** (with offline grace period)
4. **Cloud Backup** (encrypt, compress, upload)
5. **Razorpay Integration** (payment webhooks)

---

## 📞 Need Help?

If you encounter any issues:
1. Check the error message carefully
2. Verify environment variables are correct
3. Check Supabase logs in Dashboard → Logs
4. Test API endpoints with curl/Postman
5. Ask me! 😊

---

**Ready to proceed? Let me know once you've:**
1. ✅ Filled in `.env` files with Supabase credentials
2. ✅ Ran the SQL schema in Supabase
3. ✅ Created storage buckets
4. ✅ Tested the new `/api/v1` endpoints

Then we'll move to implementing JWT auth and subscription management! 🚀
