# SNAPPY Deployment Plan - Hybrid Architecture

## Overview
SNAPPY will be deployed as a **Hybrid Web + Desktop Application** with offline capabilities and cloud sync.

## Architecture

### Deployment Model
- **Web App**: Hosted on Vercel/Netlify (frontend) + Cloud provider (backend)
- **Desktop App**: Tauri-based with embedded Flask backend (PyInstaller)
- **Backend API**: Flask REST API hosted on cloud (for web + desktop online features)
- **Database**: 
  - Local: SQLite (desktop offline)
  - Cloud: PostgreSQL via Supabase (web + sync)
- **Storage**: Supabase Storage (1GB free tier) for backups

### Feature Availability

| Feature | Web | Desktop (Offline) | Desktop (Online) |
|---------|-----|-------------------|------------------|
| Invoices & Clients | ✅ | ✅ | ✅ |
| Basic PDF (LAW_001, Simple) | ✅ | ✅ | ✅ |
| Basic Analytics | ✅ | ✅ | ✅ |
| Cloud Backup | ✅ | ❌ | ✅ |
| Advanced Analytics | ✅ | ❌ | ✅ |
| Premium Templates | ✅ | ❌ | ✅ |
| Auto Updates | ✅ | ❌ | ✅ (weekly) |

## Phase 1: Backend Infrastructure (Weeks 1-2)

### 1.1 Supabase Setup
- [ ] Create Supabase project
- [ ] Set up PostgreSQL schema
  - users table
  - subscriptions table
  - license_keys table (migrate from current ProductKey)
  - backup_metadata table
- [ ] Configure Row Level Security (RLS)
- [ ] Set up Supabase Storage bucket for backups
- [ ] Create API keys and environment variables

### 1.2 Enhanced Authentication
- [ ] Implement JWT-based auth (in addition to session)
- [ ] Add license key validation endpoint
- [ ] Implement grace period for offline desktop (7 days)
- [ ] Add subscription status check
- [ ] Implement refresh token mechanism

### 1.3 Subscription Management
- [ ] Create subscription plans schema
  ```
  Plans:
  - Free Trial (7 days, all features)
  - Basic (₹X/month, basic features)
  - Pro (₹Y/month, cloud backup + advanced analytics)
  - Enterprise (₹Z/month, everything + priority support)
  ```
- [ ] Implement subscription endpoints (create, update, cancel)
- [ ] Add payment gateway integration (Razorpay/Stripe)
- [ ] Create subscription expiry checks
- [ ] Implement grace period handling

## Phase 2: Desktop App Preparation (Weeks 3-4)

### 2.1 Tauri Configuration
- [ ] Create proper tauri.conf.json with:
  - App name: "SNAPPY"
  - Identifier: "com.snappy.billing"
  - Version: "1.0.0"
  - Windows-specific config
  - Auto-updater endpoint
- [ ] Configure Tauri sidecar for Flask
- [ ] Set up PyInstaller to bundle backend
  ```
  backend_bundle/
  ├── app.exe (or python bundle)
  ├── snappy.db (template)
  ├── flask_session/
  └── templates/
  ```

### 2.2 Offline License Mechanism
- [ ] Implement license caching
  ```python
  # On first online connection
  - Fetch license from server
  - Store encrypted in local DB
  - Set expiry timestamp (7 days grace period)
  
  # On app start (offline)
  - Check cached license
  - If expired > grace period: show warning
  - If expired > grace period + 3 days: restrict features
  ```
- [ ] Add "Verify License" button in settings
- [ ] Create license renewal prompt

### 2.3 Feature Flags System
- [ ] Implement feature toggle based on:
  - Online/Offline status
  - Subscription tier
  - License validity
  ```typescript
  interface FeatureFlags {
    cloudBackup: boolean;
    advancedAnalytics: boolean;
    premiumTemplates: boolean;
    multiDeviceSync: boolean;
  }
  ```

## Phase 3: Cloud Backup Implementation (Weeks 5-6)

### 3.1 Backup Service
- [ ] Create backup API endpoints
  ```
  POST /api/backup/upload - Upload encrypted SQLite
  GET /api/backup/list - List all backups
  GET /api/backup/download/:id - Download specific backup
  POST /api/backup/restore - Restore from backup
  DELETE /api/backup/delete/:id - Delete old backup
  ```
- [ ] Implement encryption (AES-256-GCM)
  ```python
  # Encrypt before upload
  encrypted_data = encrypt_database(
      db_path='snappy.db',
      password=user_key  # Derived from license key + user password
  )
  ```
- [ ] Add compression (gzip) to reduce storage
- [ ] Implement T-1 versioning
  ```
  Retention policy:
  - Daily: Last 7 backups
  - Weekly: Last 4 backups
  - Monthly: Last 12 backups
  ```

### 3.2 Scheduled Backups (Desktop)
- [ ] Create background worker for scheduled backups
- [ ] Add user-configurable backup time
- [ ] Implement backup status UI
- [ ] Add email notifications (optional)

### 3.3 Cloud Sync (Optional for Pro+)
- [ ] Implement conflict resolution
- [ ] Add last-write-wins strategy
- [ ] Create sync status indicator
- [ ] Add manual sync trigger

## Phase 4: Web App Deployment (Week 7)

### 4.1 Frontend Deployment
- [ ] Deploy React app to Vercel/Netlify
  - Build command: `npm run build`
  - Output: `frontend/dist`
  - Environment variables: API_URL
- [ ] Configure custom domain
- [ ] Set up SSL certificate (auto via Vercel)
- [ ] Configure CORS for API

### 4.2 Backend Deployment
Options:
1. **Railway** (recommended for MVP)
   - Easy Flask deployment
   - PostgreSQL included
   - Auto-scaling
   - Cost: ~$5-10/month

2. **Heroku**
   - Established platform
   - Good Python support
   - Cost: ~$7/month (Eco dyno)

3. **DigitalOcean App Platform**
   - More control
   - Better pricing for scale
   - Cost: ~$5/month

**Choice**: Railway for now, migrate to DO later if needed

- [ ] Deploy Flask to Railway
- [ ] Connect Supabase PostgreSQL
- [ ] Set up environment variables
- [ ] Configure health check endpoint
- [ ] Set up logging (LogDNA/Papertrail)

## Phase 5: Desktop App Build Pipeline (Week 8)

### 5.1 PyInstaller Backend Bundle
- [ ] Create PyInstaller spec file
  ```python
  # backend/snappy.spec
  a = Analysis(
      ['app/main.py'],
      pathex=[],
      binaries=[],
      datas=[
          ('app/templates', 'templates'),
          ('app/static', 'static'),
      ],
      hiddenimports=['flask', 'reportlab', 'duckdb'],
      hookspath=[],
      hooksconfig={},
      runtime_hooks=[],
      excludes=[],
      win_no_prefer_redirects=False,
      win_private_assemblies=False,
      cipher=None,
      noarchive=False,
  )
  ```
- [ ] Test bundled backend executable
- [ ] Optimize bundle size (exclude unnecessary packages)

### 5.2 Tauri Build
- [ ] Configure Tauri resources
  - Copy backend bundle to resources
  - Add icon assets (Windows .ico)
  - Configure installer wizard
- [ ] Build Windows installer
  ```bash
  cd frontend
  npm run tauri:build
  ```
- [ ] Test installation flow
- [ ] Test offline functionality

### 5.3 Auto-Updater Setup
- [ ] Create update server/endpoint
  ```json
  // Update manifest
  {
    "version": "1.0.1",
    "url": "https://releases.snappy.app/snappy-1.0.1-x64.msi",
    "signature": "...",
    "notes": "Bug fixes and improvements",
    "pub_date": "2025-10-31T10:00:00Z"
  }
  ```
- [ ] Configure weekly update check
- [ ] Implement force update for security patches
- [ ] Add update UI (download progress, changelog)

## Phase 6: CI/CD Pipeline (Week 9)

### 6.1 GitHub Actions - Web App
```yaml
# .github/workflows/deploy-web.yml
name: Deploy Web App
on:
  push:
    branches: [main]
jobs:
  deploy-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - run: cd frontend && npm ci
      - run: cd frontend && npm run build
      - uses: amondnet/vercel-action@v20
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          
  deploy-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: cd backend && pip install -r requirements.txt
      - run: pytest backend/tests
      - uses: railway/deploy-action@v1
        with:
          railway-token: ${{ secrets.RAILWAY_TOKEN }}
```

### 6.2 GitHub Actions - Desktop App
```yaml
# .github/workflows/build-desktop.yml
name: Build Desktop App
on:
  push:
    tags:
      - 'v*'
jobs:
  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - uses: actions/setup-node@v3
      
      # Build backend bundle
      - run: cd backend && pip install -r requirements.txt
      - run: cd backend && pip install pyinstaller
      - run: cd backend && pyinstaller snappy.spec
      
      # Build Tauri app
      - run: cd frontend && npm ci
      - run: cd frontend && npm run tauri:build
      
      # Upload to GitHub Releases
      - uses: softprops/action-gh-release@v1
        with:
          files: |
            frontend/src-tauri/target/release/bundle/msi/*.msi
```

## Phase 7: Testing & QA (Week 10)

### 7.1 Web App Testing
- [ ] Cross-browser testing (Chrome, Firefox, Edge, Safari)
- [ ] Mobile responsive testing
- [ ] Performance testing (Lighthouse score > 90)
- [ ] Security audit (OWASP)
- [ ] Load testing (simulate 100 concurrent users)

### 7.2 Desktop App Testing
- [ ] Windows installation testing (clean installs)
- [ ] Offline mode testing (all features)
- [ ] Online/offline transition testing
- [ ] License validation testing
- [ ] Update mechanism testing
- [ ] Backup/restore testing
- [ ] Performance benchmarking

### 7.3 Integration Testing
- [ ] Web to Desktop sync
- [ ] Payment flow (Razorpay test mode)
- [ ] Subscription lifecycle
- [ ] Email notifications
- [ ] Error handling and recovery

## Phase 8: Launch Preparation (Week 11-12)

### 8.1 Documentation
- [ ] User documentation (web + desktop)
- [ ] Installation guide (desktop)
- [ ] Troubleshooting guide
- [ ] API documentation
- [ ] Developer documentation

### 8.2 Marketing Site
- [ ] Landing page
- [ ] Pricing page
- [ ] Features comparison
- [ ] FAQ
- [ ] Download page (desktop app)
- [ ] Contact/support page

### 8.3 Support Infrastructure
- [ ] Set up support email
- [ ] Create knowledge base
- [ ] Set up crash reporting (Sentry)
- [ ] Analytics (Plausible/Fathom for privacy)
- [ ] User feedback mechanism

## Cost Breakdown (Monthly)

### Free Tier Resources
- Supabase: 1GB storage + PostgreSQL (Free)
- Vercel: Frontend hosting (Free for hobby)
- GitHub: Releases hosting (Free)
- Total Free: ₹0

### Paid Services (Starting)
- Railway (Backend API): ~$10/month (₹800)
- Domain (.app): ~$12/year (₹100/month)
- Email (Google Workspace): ₹125/month
- Sentry (Error tracking): Free tier initially
- **Total: ~₹1,025/month**

### After Scale (>1000 users)
- Railway/DO: ₹2,000-5,000/month
- Supabase Pro: $25/month (₹2,000)
- CDN: ₹500-1,000/month
- Email service: ₹500/month
- **Total: ~₹5,000-8,500/month**

## Revenue Model

### Subscription Tiers
```
1. Free Trial
   - 7 days full access
   - All features unlocked
   - 1 user only

2. Starter (₹299/month or ₹2,999/year)
   - Unlimited invoices
   - Basic templates (Simple, LAW_001)
   - Local backup only
   - 1 user
   - Email support

3. Professional (₹599/month or ₹5,999/year)
   - Everything in Starter
   - Cloud backup (1GB)
   - Advanced analytics
   - Premium templates (5+)
   - 3 users
   - Priority email support

4. Enterprise (₹1,499/month or ₹14,999/year)
   - Everything in Professional
   - Unlimited cloud backup
   - Custom templates
   - Multi-device sync
   - Unlimited users
   - Dedicated support
   - Custom integrations
   - On-premise option
```

### Breakeven Analysis
- Cost per user: ~₹10/month (at scale)
- Average revenue per user: ₹599/month (Pro tier)
- Breakeven: ~20-30 paying users
- Profitable: >50 users

## Timeline Summary

| Week | Phase | Deliverable |
|------|-------|-------------|
| 1-2 | Backend Infrastructure | Supabase setup, auth, subscriptions |
| 3-4 | Desktop Prep | Tauri config, offline license, feature flags |
| 5-6 | Cloud Backup | Backup API, encryption, sync |
| 7 | Web Deployment | Live web app |
| 8 | Desktop Build | Windows installer with auto-update |
| 9 | CI/CD | Automated deployments |
| 10 | Testing | Full QA |
| 11-12 | Launch | Documentation, marketing, go-live |

**Total Time: 12 weeks (3 months)**

## Immediate Next Steps (This Week)

1. **Set up Supabase project** (Day 1)
2. **Create subscription schema** (Day 2)
3. **Implement JWT auth** (Day 3-4)
4. **Create Tauri config** (Day 5)
5. **Test PyInstaller bundle** (Day 6-7)

---

## Notes

- Unsigned installers will show SmartScreen warnings on Windows - document this for users
- Consider adding code signing certificate (~₹25,000) once revenue reaches ₹50,000/month
- Keep backend API stateless for easy horizontal scaling
- Monitor Supabase free tier limits (500MB database, 1GB storage)
- Consider upgrading to Supabase Pro ($25/mo) once >100 users
