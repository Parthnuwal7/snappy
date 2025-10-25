# SNAPPY Configuration Summary

## 🎯 Key Decisions Made

### **Deployment Model**
- **Type:** Hybrid Web + Desktop App
- **Platform Priority:** Windows desktop first, then web (all platforms)
- **Offline Mode:** Desktop app works offline for 7 days (grace period)

### **API Configuration**
- **Base URL:** `/api/v1/` (versioned)
- **Example:** `http://localhost:5000/api/v1/auth/login`
- **Version:** v1 (allows future v2, v3 without breaking changes)

### **Subscription Pricing**
```
Starter:     ₹400/month  or  ₹4,000/year  (₹333/month equivalent)
Pro:       ₹1,000/month  or  ₹10,000/year  (₹833/month equivalent)
Enterprise: ₹1,500/month  or  ₹15,000/year  (₹1,250/month equivalent)
```

### **Free Trial**
- **Duration:** 7 days
- **Access:** All features unlocked (same as Enterprise)
- **Activation:** No credit card required upfront

### **Payment Gateway**
- **Provider:** Razorpay
- **Currency:** INR (₹)
- **GST:** To be added to invoices

### **Company Details**
- **App Name:** SNAPPY
- **Publisher:** Parth Nuwal
- **Installer Shows:** "Published by: Parth Nuwal"

### **Code Signing**
- **Initial:** Unsigned (to minimize costs)
- **After Revenue Breakeven:** Purchase certificate (~₹25,000/year)

---

## 📦 Infrastructure Stack

### **Frontend**
- **Framework:** React 18 + TypeScript + Vite
- **Hosting (Web):** Vercel (free tier)
- **Hosting (Desktop):** Bundled with Tauri

### **Backend**
- **Framework:** Flask 3.0 (Python)
- **Hosting (Web):** Railway (~₹800/month to start)
- **Hosting (Desktop):** PyInstaller bundle (embedded)

### **Database**
- **Cloud:** PostgreSQL via Supabase (500MB free)
- **Local:** SQLite (desktop offline mode)
- **Analytics:** DuckDB (local aggregations)

### **Storage**
- **Provider:** Supabase Storage (1GB free)
- **Buckets:**
  - `user-backups` (encrypted DB backups)
  - `user-uploads` (logos, signatures, QR codes)
  - `invoice-pdfs` (optional, premium feature)

### **Authentication**
- **Web:** Session-based (HttpOnly cookies)
- **Desktop:** JWT tokens (7-day expiry with offline grace)
- **Security:** Row Level Security (RLS) in Supabase

---

## 🔑 License Key System (Decoupled)

### **How It Works**
1. Separate payment website (to be built)
2. User pays → Razorpay webhook → Generate key
3. Key format: `SNAPPY-XXXX-XXXX-XXXX-XXXX`
4. Key sent via email
5. User enters key in desktop app
6. Key validated against Supabase
7. Key bound to device_id (one key per device)

### **Key Benefits**
- ✅ Keys can be generated/sold independently
- ✅ No need to integrate payment into main app
- ✅ Can create bulk keys for resellers
- ✅ Easy refund/transfer management
- ✅ Can sell keys on multiple platforms

---

## 🎨 Feature Availability Matrix

| Feature | Web (Online) | Desktop (Offline) | Desktop (Online) |
|---------|-------------|-------------------|------------------|
| **Core** |
| Create Invoices | ✅ | ✅ | ✅ |
| Manage Clients | ✅ | ✅ | ✅ |
| Basic PDF (LAW_001, Simple) | ✅ | ✅ | ✅ |
| Basic Analytics | ✅ | ✅ | ✅ |
| CSV Import/Export | ✅ | ✅ | ✅ |
| **Premium** |
| Cloud Backup | ✅ | ❌ | ✅ (Pro+) |
| Advanced Analytics | ✅ | ❌ | ✅ (Pro+) |
| Premium Templates | ✅ | ❌ | ✅ (Pro+) |
| Multi-Device Sync | ✅ | ❌ | ✅ (Pro+) |
| Custom Templates | ✅ | ❌ | ✅ (Enterprise only) |
| API Access | ✅ | ❌ | ✅ (Enterprise only) |

---

## 🔄 Update Strategy

### **Desktop App**
- **Frequency:** Weekly check
- **User Control:** Can update now or later
- **Security Updates:** Forced (cannot skip)
- **Method:** Tauri auto-updater
- **Signed:** No (initially, to save costs)

### **Web App**
- **Frequency:** Instant (on deploy)
- **User Control:** None needed (automatic)
- **Rollout:** 10% → 50% → 100% (gradual)

---

## 💾 Backup Strategy

### **Desktop to Cloud**
- **Trigger:** Manual or scheduled (daily at user-set time)
- **Process:**
  1. Close DB connections
  2. Compress with gzip
  3. Encrypt with AES-256-GCM
  4. Upload to Supabase Storage
  5. Save metadata in PostgreSQL
  
### **Encryption Key**
- **Derived from:** `SHA256(license_key + user_password)`
- **Security:** User must remember password to restore

### **Retention Policy**
- Daily backups: Keep last 7
- Weekly backups: Keep last 4
- Monthly backups: Keep last 12

---

## 📊 Cost Projection

### **Initial (0-100 users)**
- Supabase: ₹0 (free tier - 500MB DB, 1GB storage)
- Vercel: ₹0 (free tier)
- Railway: ₹800/month
- Domain: ₹100/month
- **Total: ~₹900/month** ✅

### **Growth (100-1000 users)**
- Supabase Pro: ₹2,000/month (more resources)
- Railway scaled: ₹2,000-5,000/month
- CDN (Cloudflare): ₹500/month
- Email service: ₹500/month
- **Total: ~₹5,000-8,000/month**

### **Scale (1000+ users)**
- Consider migrating to:
  - DigitalOcean App Platform
  - AWS/Azure (more control)
  - Dedicated servers

### **One-Time Costs (After Revenue)**
- Code signing certificate: ₹25,000/year
- Apple Developer: ₹8,000/year (for macOS)

---

## 🎯 Revenue Projections

### **Conservative (First 6 Months)**
```
Assume:
- 100 total signups
- 20% conversion (20 paying users)
- 10 Starter, 8 Pro, 2 Enterprise

Monthly Revenue:
(10 × ₹400) + (8 × ₹1,000) + (2 × ₹1,500) = ₹15,000/month

Annual Revenue: ₹1,80,000
```

### **Optimistic (After 1 Year)**
```
Assume:
- 500 total signups
- 30% conversion (150 paying users)
- 50 Starter, 80 Pro, 20 Enterprise

Monthly Revenue:
(50 × ₹400) + (80 × ₹1,000) + (20 × ₹1,500) = ₹1,30,000/month

Annual Revenue: ₹15,60,000
```

### **Breakeven**
```
Costs: ~₹5,000-8,000/month
Need: ~20-30 paying users (mix of tiers)
Timeline: 3-6 months realistic
```

---

## 🚀 Go-To-Market Strategy

### **Phase 1: Soft Launch (Month 1-2)**
- Invite-only beta
- 50-100 early users
- Gather feedback
- Fix critical bugs
- Build case studies

### **Phase 2: Public Launch (Month 3-4)**
- Launch website
- Product Hunt launch
- Social media campaign
- Free trial for all

### **Phase 3: Growth (Month 5-12)**
- Paid ads (Google, Facebook)
- Content marketing
- Lawyer associations outreach
- Referral program
- Partnership with law schools

---

## 🎓 Target Audience

### **Primary**
- Individual lawyers (solo practitioners)
- Small law firms (2-5 partners)
- CA/Chartered Accountants

### **Secondary**
- Consultants
- Freelance professionals
- Service-based businesses

### **Market Size (India)**
- ~1.3 million registered lawyers
- ~100,000 CAs
- Potential market: 50,000-100,000 paid users

---

## 📱 Platform Roadmap

### **Phase 1 (Now)** ✅
- Windows desktop app
- Web app (responsive)

### **Phase 2 (6 months)**
- macOS desktop app
- Linux AppImage

### **Phase 3 (12 months)**
- Mobile companion app (iOS/Android)
- View invoices on phone
- Send payment reminders
- Quick invoice creation

---

## 🔒 Security Measures

### **Data Protection**
- ✅ Row Level Security (RLS) in Supabase
- ✅ Encrypted backups (AES-256-GCM)
- ✅ HTTPS only in production
- ✅ HttpOnly cookies (no XSS)
- ✅ CSRF protection (SameSite cookies)
- ✅ Rate limiting on API endpoints
- ✅ SQL injection protection (parameterized queries)

### **Compliance**
- GDPR-ready (data export, right to deletion)
- Indian data residency (Supabase Mumbai region)
- GST compliance (invoice generation)
- Payment security (PCI-DSS via Razorpay)

---

## 📋 Next Implementation Steps

### **This Week**
1. ✅ Fill `.env` with Supabase credentials
2. ✅ Run SQL schema in Supabase
3. ✅ Create storage buckets
4. ✅ Test new `/api/v1` endpoints

### **Next Week**
1. Implement JWT authentication
2. Create subscription API endpoints
3. Build license validation system
4. Test offline grace period

### **Week After**
1. Implement cloud backup service
2. Add encryption/compression
3. Create backup UI in settings
4. Test restore functionality

---

## ✅ Summary

**You now have:**
- ✅ API versioning (`/api/v1`)
- ✅ Complete database schema
- ✅ Environment configuration templates
- ✅ Subscription pricing defined
- ✅ Architecture documented
- ✅ Deployment plan ready

**Next: Fill in your Supabase credentials and run the schema!** 🚀
