# SNAPPY Deployment - Immediate Action Items

## 🚀 What We're Building
**Hybrid Web + Desktop App** with offline capabilities, cloud sync, and subscription management.

---

## 📅 THIS WEEK (Week 1) - Foundation

### Day 1: Supabase Setup ✅ Ready to implement
```bash
# Tasks:
1. Create Supabase account (free tier)
2. Create new project "snappy-production"
3. Note down:
   - Project URL: https://xxxxx.supabase.co
   - Anon key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   - Service role key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**I can help with:**
- Database schema creation SQL
- Row Level Security policies
- Storage bucket configuration

---

### Day 2: Enhanced Database Schema
**Migrate from SQLite-only to hybrid SQLite + PostgreSQL**

#### Current Schema (SQLite - stays for desktop offline)
```sql
-- Local only (desktop app)
- clients
- invoices
- invoice_items
```

#### New Cloud Schema (PostgreSQL - Supabase)
```sql
-- User management
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  last_login TIMESTAMP,
  is_active BOOLEAN DEFAULT TRUE
);

-- Subscriptions
CREATE TABLE subscriptions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  plan_type TEXT NOT NULL, -- 'trial', 'starter', 'pro', 'enterprise'
  status TEXT NOT NULL, -- 'active', 'expired', 'cancelled'
  started_at TIMESTAMP DEFAULT NOW(),
  expires_at TIMESTAMP NOT NULL,
  stripe_subscription_id TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

-- License Keys (migrate from current ProductKey model)
CREATE TABLE license_keys (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  key TEXT UNIQUE NOT NULL,
  device_id TEXT, -- For desktop app binding
  activated_at TIMESTAMP,
  last_validated TIMESTAMP,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Backup Metadata
CREATE TABLE backup_metadata (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  backup_type TEXT NOT NULL, -- 'daily', 'weekly', 'monthly', 'manual'
  file_path TEXT NOT NULL, -- Supabase Storage path
  file_size_bytes BIGINT,
  encrypted BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT NOW()
);
```

**I can create:**
- Complete migration SQL
- RLS policies for security
- Indexes for performance

---

### Day 3-4: JWT Authentication
**Add JWT tokens in addition to session-based auth**

Why both?
- **Sessions**: For web app (browser-based)
- **JWT**: For desktop app (API calls, offline validation)

```python
# New endpoints to create:
POST /api/auth/token - Get JWT token (login)
POST /api/auth/refresh - Refresh expired token
GET /api/auth/validate - Validate token and check subscription
```

**I can implement:**
- JWT token generation/validation
- Refresh token mechanism
- Token-based license validation

---

### Day 5-6: Tauri Configuration
**Set up proper Tauri config for desktop app**

```json
// src-tauri/tauri.conf.json (to be created)
{
  "package": {
    "productName": "SNAPPY",
    "version": "1.0.0"
  },
  "tauri": {
    "allowlist": {
      "all": false,
      "fs": {
        "all": false,
        "readFile": true,
        "writeFile": true,
        "readDir": true,
        "createDir": true,
        "scope": ["$APPDATA/snappy/*"]
      },
      "http": {
        "all": false,
        "request": true,
        "scope": ["https://api.snappy.app/*"]
      },
      "shell": {
        "sidecar": true,
        "scope": [
          {
            "name": "backend",
            "sidecar": true,
            "args": true
          }
        ]
      }
    },
    "bundle": {
      "active": true,
      "identifier": "com.snappy.billing",
      "icon": [
        "icons/icon.ico"
      ],
      "resources": [
        "backend-dist/*"
      ],
      "windows": {
        "certificateThumbprint": null,
        "digestAlgorithm": "sha256",
        "timestampUrl": ""
      }
    },
    "updater": {
      "active": true,
      "endpoints": [
        "https://releases.snappy.app/{{target}}/{{current_version}}"
      ],
      "dialog": true,
      "pubkey": "YOUR_PUBLIC_KEY_HERE"
    }
  }
}
```

**I can create:**
- Complete Tauri config
- Sidecar configuration for Flask
- Update manifest structure

---

### Day 7: PyInstaller Backend Bundle
**Test bundling Flask backend into executable**

```bash
# Install PyInstaller
cd backend
pip install pyinstaller

# Create spec file
pyi-makespec app/main.py --name snappy-backend --onefile

# Test build
pyinstaller snappy-backend.spec

# Test executable
./dist/snappy-backend.exe
```

**I can help:**
- Create optimized PyInstaller spec
- Debug bundling issues
- Optimize bundle size

---

## 🎯 NEXT WEEK (Week 2) - Core Features

### Subscription Management
- [ ] Create subscription plans in Supabase
- [ ] Implement trial logic (7 days)
- [ ] Add subscription check middleware
- [ ] Create subscription UI in settings

### Feature Flags
- [ ] Implement feature toggle system
- [ ] Detect online/offline mode
- [ ] Show appropriate UI based on subscription + online status

### Payment Integration
- [ ] Razorpay account setup
- [ ] Create payment endpoints
- [ ] Implement subscription purchase flow
- [ ] Add payment webhook handlers

---

## ⚡ Quick Wins (Can Do Anytime)

### 1. Environment Configuration
Create proper `.env` structure for different deployments:

```bash
# .env.local (development)
DATABASE_URL=sqlite:///snappy.db
API_BASE_URL=http://localhost:5000

# .env.production (web app)
DATABASE_URL=postgresql://user:pass@supabase.co:5432/postgres
API_BASE_URL=https://api.snappy.app
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGci...

# .env.desktop (desktop app defaults)
DATABASE_URL=sqlite:///${APPDATA}/snappy/snappy.db
API_BASE_URL=https://api.snappy.app
OFFLINE_GRACE_PERIOD_DAYS=7
```

### 2. Feature Detection Utility
```typescript
// frontend/src/utils/features.ts
interface FeatureAccess {
  cloudBackup: boolean;
  advancedAnalytics: boolean;
  premiumTemplates: boolean;
  multiDeviceSync: boolean;
}

export function getAvailableFeatures(
  isOnline: boolean,
  subscription: 'trial' | 'starter' | 'pro' | 'enterprise',
  isDesktop: boolean
): FeatureAccess {
  // Logic to determine what features are available
  // based on online status, subscription tier, and platform
}
```

### 3. Offline Indicator Component
```typescript
// frontend/src/components/OfflineIndicator.tsx
export function OfflineIndicator() {
  const isOnline = useOnlineStatus();
  
  if (isOnline) return null;
  
  return (
    <div className="bg-yellow-100 border-l-4 border-yellow-500 p-4">
      <p className="text-yellow-700">
        ⚠️ You're offline. Some features are limited.
        <button>Learn more</button>
      </p>
    </div>
  );
}
```

---

## 🤔 Decisions Needed From You

### 1. Supabase Project Name
- What should we call the project? "snappy-prod", "snappy-app", "snappy-billing"?

### 2. API Domain
- Do you have a domain? e.g., `api.snappy.app`
- Or should we use Railway's default domain for now?

### 3. Subscription Pricing
Need exact pricing for tiers:
```
Starter: ₹___/month or ₹___/year (-17% discount)
Pro: ₹___/month or ₹___/year (-17% discount)
Enterprise: ₹___/month or ₹___/year (-17% discount)
```

### 4. Trial Period
- Confirmed 7 days?
- Credit card required upfront or after trial?
- What happens when trial expires? (Read-only? Grace period?)

### 5. Payment Gateway
- Razorpay or Stripe?
- Do you have a business account set up?
- Need GST invoice generation?

### 6. Desktop App Name
- Just "SNAPPY" or "SNAPPY Billing"?
- Company name for installer? (e.g., "SNAPPY Labs", "Your Company Name")

---

## 📊 What Should We Start With?

**Option A: Infrastructure First (Recommended)**
1. Set up Supabase (30 mins)
2. Create database schema (2 hours)
3. Deploy backend API to Railway (1 hour)
4. Test end-to-end authentication (1 hour)

**Option B: Desktop First**
1. Create Tauri config (1 hour)
2. Bundle Flask with PyInstaller (2 hours)
3. Build Windows installer (1 hour)
4. Test offline functionality (1 hour)

**Option C: Subscription First**
1. Design subscription plans (1 hour)
2. Set up Razorpay (1 hour)
3. Implement payment flow (3 hours)
4. Test trial + upgrade flow (1 hour)

---

## 💡 My Recommendation

**Start with Option A (Infrastructure First)** because:
1. ✅ Supabase setup is quick and free
2. ✅ Backend API is needed for both web and desktop
3. ✅ Easiest to test and iterate
4. ✅ Unblocks other work (subscription, desktop app)

Once infrastructure is ready, we can parallelize:
- Desktop app packaging
- Subscription implementation
- Payment integration

---

## 🛠️ What Can I Help With RIGHT NOW?

I can immediately create:

1. **Supabase SQL Schema** - Complete migration script
2. **JWT Auth Implementation** - Add token-based auth to Flask
3. **Tauri Config** - Full tauri.conf.json with sidecar
4. **PyInstaller Spec** - Optimized backend bundling
5. **Feature Flags System** - TypeScript + Python implementation
6. **Subscription API** - CRUD endpoints for subscriptions
7. **Environment Config** - Proper .env structure
8. **CI/CD Workflow** - GitHub Actions for automated builds

**Just tell me which one to start with!** 🚀
