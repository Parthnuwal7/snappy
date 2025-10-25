# SNAPPY Hybrid Architecture - Visual Guide

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              END USERS                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│   ┌──────────────────────┐              ┌──────────────────────────┐       │
│   │   Web Browser        │              │   Desktop App (Tauri)    │       │
│   │   ───────────────    │              │   ────────────────────   │       │
│   │   • Chrome/Firefox   │              │   • Windows .msi         │       │
│   │   • Always Online    │              │   • Offline Capable      │       │
│   │   • Responsive UI    │              │   • Auto Updates         │       │
│   └──────────────────────┘              └──────────────────────────┘       │
│            │                                      │       │                  │
│            │ HTTPS                                │ HTTPS │ Local IPC        │
│            │                                      │       │                  │
└────────────┼──────────────────────────────────────┼───────┼──────────────────┘
             │                                      │       │
             │                                      │       │
             ▼                                      ▼       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND LAYER                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│   ┌──────────────────────────────────────────────────────────────────────┐ │
│   │                    React 18 + TypeScript                              │ │
│   │                    ───────────────────────                            │ │
│   │                                                                        │ │
│   │   ┌─────────────┐  ┌──────────────┐  ┌──────────────┐              │ │
│   │   │   Pages     │  │  Components  │  │    Hooks     │              │ │
│   │   │  ────────   │  │  ──────────  │  │  ──────────  │              │ │
│   │   │ • Dashboard │  │ • Invoice    │  │ • useAuth    │              │ │
│   │   │ • Invoices  │  │ • Client     │  │ • useOnline  │              │ │
│   │   │ • Clients   │  │ • Analytics  │  │ • useFeature │              │ │
│   │   │ • Settings  │  │ • PDF        │  │ • useBackup  │              │ │
│   │   └─────────────┘  └──────────────┘  └──────────────┘              │ │
│   │                                                                        │ │
│   │   ┌──────────────────────────────────────────────────────────────┐  │ │
│   │   │              State Management (Zustand)                       │  │ │
│   │   │              ──────────────────────────                       │  │ │
│   │   │  • Auth State  • Feature Flags  • Subscription State          │  │ │
│   │   └──────────────────────────────────────────────────────────────┘  │ │
│   │                                                                        │ │
│   │   ┌──────────────────────────────────────────────────────────────┐  │ │
│   │   │              Platform Detection                               │  │ │
│   │   │              ──────────────────                               │  │ │
│   │   │  isDesktop = window.__TAURI__ !== undefined                   │  │ │
│   │   │  isOnline = navigator.onLine                                  │  │ │
│   │   └──────────────────────────────────────────────────────────────┘  │ │
│   └──────────────────────────────────────────────────────────────────────┘ │
│                                                                               │
│   Deployment:                                                                │
│   • Web: Vercel (https://app.snappy.app)                                   │
│   • Desktop: Bundled with Tauri (file:// protocol)                         │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
             │                                      │
             │ REST API                             │ REST API / Local
             │                                      │
             ▼                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BACKEND LAYER                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│   ┌─────────────────────────────────┐  ┌──────────────────────────────┐    │
│   │   Cloud Backend (Flask)         │  │  Embedded Backend (Desktop)  │    │
│   │   ───────────────────────        │  │  ────────────────────────    │    │
│   │                                  │  │                               │    │
│   │   Hosted: Railway/Heroku/DO     │  │  Bundled: PyInstaller        │    │
│   │   URL: https://api.snappy.app   │  │  Port: localhost:5001        │    │
│   │                                  │  │  Process: Tauri Sidecar      │    │
│   │   ┌──────────────────────────┐  │  │                               │    │
│   │   │   API Routes             │  │  │  Same Flask app, but:        │    │
│   │   │   ──────────             │  │  │  • Uses SQLite only          │    │
│   │   │   /api/auth              │  │  │  • Cached license validation │    │
│   │   │   /api/invoices          │  │  │  • No cloud features         │    │
│   │   │   /api/clients           │  │  │  • Bundled with app          │    │
│   │   │   /api/analytics         │  │  │                               │    │
│   │   │   /api/backup            │  │  └──────────────────────────────┘    │
│   │   │   /api/subscription      │  │                                       │
│   │   └──────────────────────────┘  │                                       │
│   │                                  │                                       │
│   │   ┌──────────────────────────┐  │                                       │
│   │   │   Middleware             │  │                                       │
│   │   │   ──────────             │  │                                       │
│   │   │   • CORS                 │  │                                       │
│   │   │   • JWT Auth             │  │                                       │
│   │   │   • Subscription Check   │  │                                       │
│   │   │   • Rate Limiting        │  │                                       │
│   │   │   • Error Handling       │  │                                       │
│   │   └──────────────────────────┘  │                                       │
│   └─────────────────────────────────┘                                       │
│                   │                                                           │
│                   │                                                           │
│                   ▼                                                           │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                    Business Logic Layer                              │  │
│   │                    ────────────────────                              │  │
│   │                                                                        │  │
│   │   ┌──────────────┐  ┌──────────────┐  ┌───────────────┐            │  │
│   │   │  Invoice     │  │  PDF Gen     │  │  Analytics    │            │  │
│   │   │  Service     │  │  Service     │  │  Service      │            │  │
│   │   │  ────────    │  │  ────────    │  │  ─────────    │            │  │
│   │   │ • CRUD       │  │ • ReportLab  │  │ • DuckDB      │            │  │
│   │   │ • Validation │  │ • Templates  │  │ • Aggregation │            │  │
│   │   └──────────────┘  └──────────────┘  └───────────────┘            │  │
│   │                                                                        │  │
│   │   ┌──────────────┐  ┌──────────────┐  ┌───────────────┐            │  │
│   │   │  Backup      │  │  License     │  │  Subscription │            │  │
│   │   │  Service     │  │  Service     │  │  Service      │            │  │
│   │   │  ────────    │  │  ────────    │  │  ───────────  │            │  │
│   │   │ • Encrypt    │  │ • Validate   │  │ • Check Tier  │            │  │
│   │   │ • Compress   │  │ • Cache      │  │ • Update      │            │  │
│   │   │ • Upload     │  │ • Grace      │  │ • Webhook     │            │  │
│   │   └──────────────┘  └──────────────┘  └───────────────┘            │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
                   │                              │
                   │                              │
                   ▼                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATA LAYER                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│   ┌──────────────────────────────────┐  ┌──────────────────────────────┐   │
│   │   PostgreSQL (Supabase)          │  │  SQLite (Desktop Local)      │   │
│   │   ────────────────────            │  │  ──────────────────────      │   │
│   │                                   │  │                               │   │
│   │   Location: Cloud (Free Tier)    │  │  Location: %APPDATA%/snappy  │   │
│   │   Size: 500MB included           │  │  Size: Unlimited (local)     │   │
│   │                                   │  │                               │   │
│   │   Tables:                         │  │  Tables:                     │   │
│   │   • users                         │  │  • clients                   │   │
│   │   • subscriptions                 │  │  • invoices                  │   │
│   │   • license_keys                  │  │  • invoice_items             │   │
│   │   • backup_metadata               │  │  • cached_license            │   │
│   │   • payment_history               │  │  • settings                  │   │
│   │                                   │  │                               │   │
│   │   Features:                       │  │  Features:                   │   │
│   │   • Auto backups                  │  │  • Fast local access         │   │
│   │   • Row Level Security            │  │  • Offline capable           │   │
│   │   • Real-time subscriptions       │  │  • Portable (backup)         │   │
│   └──────────────────────────────────┘  └──────────────────────────────┘   │
│                                                                               │
│   ┌──────────────────────────────────┐  ┌──────────────────────────────┐   │
│   │   Supabase Storage               │  │  DuckDB (Analytics)          │   │
│   │   ────────────────               │  │  ──────────────────          │   │
│   │                                   │  │                               │   │
│   │   Location: Cloud                │  │  Location: Local             │   │
│   │   Size: 1GB free                 │  │  File: snappy_analytics.db   │   │
│   │                                   │  │                               │   │
│   │   Stored:                         │  │  Used For:                   │   │
│   │   • Encrypted DB backups          │  │  • Monthly revenue charts    │   │
│   │   • User uploaded files           │  │  • Top clients analysis      │   │
│   │   • Invoice PDFs (premium)        │  │  • Aging reports             │   │
│   │                                   │  │  • Fast aggregations         │   │
│   │   Retention:                      │  │                               │   │
│   │   • Daily: 7 days                 │  │  Synced from SQLite daily    │   │
│   │   • Weekly: 4 weeks               │  │                               │   │
│   │   • Monthly: 12 months            │  │                               │   │
│   └──────────────────────────────────┘  └──────────────────────────────┘   │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Data Flow: Invoice Creation

### Web App (Online)
```
User creates invoice
    ↓
React form submits
    ↓
POST /api/invoices (Cloud Backend)
    ↓
JWT validation
    ↓
Subscription check (has access?)
    ↓
Save to PostgreSQL
    ↓
Sync to DuckDB for analytics
    ↓
Return invoice JSON
    ↓
React updates UI
```

### Desktop App (Offline)
```
User creates invoice
    ↓
React form submits
    ↓
POST http://localhost:5001/api/invoices (Local Backend)
    ↓
Cached license validation (grace period check)
    ↓
Save to local SQLite
    ↓
Update local DuckDB
    ↓
Return invoice JSON
    ↓
React updates UI
    ↓
[When online] Background sync to cloud
```

---

## 🔐 Authentication Flow

### Web App
```
1. User logs in with email/password
   ↓
2. POST /api/auth/login
   ↓
3. Backend validates credentials (PostgreSQL)
   ↓
4. Generate JWT token + Refresh token
   ↓
5. Set HttpOnly cookie (session)
   ↓
6. Return tokens + user data
   ↓
7. Frontend stores in memory (Zustand)
   ↓
8. All API calls include Authorization: Bearer <token>
```

### Desktop App
```
1. User logs in with email/password
   ↓
2. POST https://api.snappy.app/api/auth/login
   ↓
3. Backend validates credentials
   ↓
4. Check license key for this device_id
   ↓
5. Generate JWT with extended expiry (7 days)
   ↓
6. Return token + license data
   ↓
7. Desktop stores encrypted in local DB
   ↓
8. Desktop can work offline for 7 days
   ↓
9. After 7 days, require revalidation
```

---

## 💾 Backup Flow

### Manual Backup (Desktop → Cloud)
```
User clicks "Backup Now" in Settings
    ↓
1. Close all DB connections
    ↓
2. Copy snappy.db to temp location
    ↓
3. Compress with gzip
    ↓
4. Encrypt with AES-256-GCM
   (Key derived from: license_key + user_password)
    ↓
5. Upload to Supabase Storage
   POST /api/backup/upload
    ↓
6. Save metadata to PostgreSQL
   (backup_metadata table)
    ↓
7. Delete temp files
    ↓
8. Show success notification
```

### Auto Backup (Scheduled)
```
Desktop app checks time every hour
    ↓
If scheduled time reached (e.g., 2 AM)
    ↓
Check if online
    ↓
If subscription includes cloud backup
    ↓
Run manual backup flow
    ↓
Send email notification (optional)
```

### Restore (Cloud → Desktop)
```
User clicks "Restore from Backup"
    ↓
1. Fetch backup list from API
   GET /api/backup/list
    ↓
2. User selects backup (shows date, size)
    ↓
3. Download encrypted file from Supabase Storage
    ↓
4. Decrypt with user's password
    ↓
5. Verify integrity (checksum)
    ↓
6. Create backup of current DB (safety)
    ↓
7. Replace current DB with restored one
    ↓
8. Restart app / Reload data
```

---

## 🎯 Feature Availability Matrix

```typescript
// frontend/src/utils/features.ts

export type SubscriptionTier = 'trial' | 'starter' | 'pro' | 'enterprise';

export interface FeatureConfig {
  cloudBackup: boolean;
  advancedAnalytics: boolean;
  premiumTemplates: boolean;
  multiDeviceSync: boolean;
  customTemplates: boolean;
  apiAccess: boolean;
  prioritySupport: boolean;
}

export function getFeatures(
  tier: SubscriptionTier,
  isOnline: boolean,
  isDesktop: boolean
): FeatureConfig {
  const baseFeatures = {
    trial: {
      cloudBackup: true,
      advancedAnalytics: true,
      premiumTemplates: true,
      multiDeviceSync: true,
      customTemplates: false,
      apiAccess: false,
      prioritySupport: false,
    },
    starter: {
      cloudBackup: false, // ❌ Not included
      advancedAnalytics: false,
      premiumTemplates: false,
      multiDeviceSync: false,
      customTemplates: false,
      apiAccess: false,
      prioritySupport: false,
    },
    pro: {
      cloudBackup: true, // ✅ Included
      advancedAnalytics: true,
      premiumTemplates: true,
      multiDeviceSync: true,
      customTemplates: false,
      apiAccess: false,
      prioritySupport: true,
    },
    enterprise: {
      cloudBackup: true,
      advancedAnalytics: true,
      premiumTemplates: true,
      multiDeviceSync: true,
      customTemplates: true, // ✅ Enterprise only
      apiAccess: true, // ✅ Enterprise only
      prioritySupport: true,
    },
  };

  let features = baseFeatures[tier];

  // Disable online-only features if offline
  if (!isOnline) {
    features = {
      ...features,
      cloudBackup: false,
      advancedAnalytics: false,
      premiumTemplates: false,
      multiDeviceSync: false,
      apiAccess: false,
    };
  }

  return features;
}
```

---

## 📱 Update Flow (Desktop Only)

```
Desktop app starts
    ↓
Check last update check timestamp
    ↓
If > 7 days, check for updates
    ↓
GET https://releases.snappy.app/updates.json
    ↓
Compare current version vs latest
    ↓
If update available:
  ┌─────────────────────────────────┐
  │  New version available: 1.0.1   │
  │  ───────────────────────────    │
  │                                  │
  │  Changes:                        │
  │  • Bug fixes                     │
  │  • New PDF template              │
  │                                  │
  │  [Update Now] [Update Tonight]  │
  └─────────────────────────────────┘
    ↓
If security update (force=true):
  ┌─────────────────────────────────┐
  │  Security Update Required        │
  │  ────────────────────────        │
  │                                  │
  │  Critical security patch         │
  │  available. Update now.          │
  │                                  │
  │  [Update Now] (no skip option)  │
  └─────────────────────────────────┘
    ↓
Download update.msi in background
    ↓
Show progress (0% → 100%)
    ↓
When complete, prompt to restart
    ↓
Close app, run installer
    ↓
Installer updates files
    ↓
Restart app with new version
```

---

## 🔧 Configuration Files

### Desktop App Paths
```
Windows:
  App: C:\Program Files\SNAPPY\snappy.exe
  Data: C:\Users\<user>\AppData\Roaming\SNAPPY\
    ├── snappy.db (SQLite)
    ├── snappy_analytics.duckdb
    ├── flask_session/
    ├── logs/
    │   ├── app.log
    │   └── backend.log
    └── config.json

macOS (future):
  App: /Applications/SNAPPY.app
  Data: ~/Library/Application Support/SNAPPY/

Linux (future):
  App: /opt/snappy/
  Data: ~/.local/share/snappy/
```

### Environment Variables
```bash
# Web App (.env.production)
VITE_API_URL=https://api.snappy.app
VITE_APP_VERSION=1.0.0
VITE_SUPABASE_URL=https://xxxxx.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGci...

# Desktop App (embedded in build)
API_URL=https://api.snappy.app
LOCAL_BACKEND_PORT=5001
OFFLINE_GRACE_DAYS=7
AUTO_UPDATE_URL=https://releases.snappy.app/updates.json
```

---

## 🚦 Decision Tree: Web vs Desktop

```
User needs SNAPPY
    │
    ├─ Wants offline access? ──NO──> Use Web App
    │                                 ├─ Access anywhere
    │                                 ├─ Always up-to-date
    │                                 └─ No installation
    │
    └─ YES ──> Use Desktop App
              ├─ Works without internet
              ├─ Faster performance
              ├─ Local data privacy
              └─ Can still sync to cloud
```

---

This architecture gives you the best of both worlds:
- **Web app**: Easy access, always updated, works on any OS
- **Desktop app**: Offline capable, faster, more private

Users can even use both simultaneously - data syncs between them! 🎉
