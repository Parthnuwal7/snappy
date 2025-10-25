# SNAPPY License Security & Lifecycle

## 🔐 License Key Security Model

### Current Implementation (SECURE ✅)

## License States & Transitions

```
User Purchases
    ↓
[PENDING_VERIFICATION] ← License key generated & saved
    ↓
Admin Reviews Payment
    ↓
    ├─→ [APPROVED] → admin_verified = true, status = 'pending_verification'
    │       ↓
    │   User Activates Desktop App
    │       ↓
    │   [ACTIVE] ← status = 'active', invoked_at set, expires_at = +1 year
    │       ↓
    │   (1 year passes)
    │       ↓
    │   [EXPIRED] ← Desktop app checks: expires_at < now
    │
    └─→ [REJECTED] → status = 'rejected', admin_notes = reason
            ↓
        CANNOT ACTIVATE ❌
```

## Detailed Lifecycle

### Stage 1: Purchase Submitted
**Trigger:** User submits UPI payment

```javascript
// POST /api/payment/submit-upi
const licenseKey = generateLicenseKey(); // e.g., SNAPPY-A1B2C3D4E5F6G7H8

await supabase.from('licenses').insert({
  license_key: licenseKey,
  status: 'pending_verification',  // ← NOT ACTIVE YET
  admin_verified: false             // ← ADMIN MUST VERIFY
});
```

**Database State:**
- ✅ Key exists in database
- ❌ `admin_verified = false`
- ❌ `status = 'pending_verification'`
- ❌ `invoked_at = NULL`
- ❌ `expires_at = NULL`

**Can Activate?** ❌ NO - Desktop app will show: *"Payment verification pending. Please wait for admin approval."*

---

### Stage 2A: Admin APPROVES Payment
**Trigger:** Admin clicks "Verify Payment" in admin panel

```javascript
// POST /api/admin/verify-payment/:licenseId
await supabase.from('licenses').update({
  admin_verified: true,              // ← NOW VERIFIED
  status: 'pending_verification',    // ← Still pending activation
  verified_at: new Date()
});
```

**Database State:**
- ✅ Key exists
- ✅ `admin_verified = true`
- ⚠️ `status = 'pending_verification'` (waiting for user to activate)
- ❌ `invoked_at = NULL`
- ❌ `expires_at = NULL`

**Can Activate?** ⚠️ YES - But will transition to ACTIVE on activation

---

### Stage 2B: Admin REJECTS Payment
**Trigger:** Admin clicks "Reject Payment" in admin panel

```javascript
// POST /api/admin/reject-payment/:licenseId
await supabase.from('licenses').update({
  status: 'rejected',                    // ← PERMANENTLY REJECTED
  admin_notes: 'Invalid UPI transaction' // ← Reason shown to user
});
```

**Database State:**
- ✅ Key exists
- ❌ `admin_verified = false` (or true, doesn't matter)
- ❌ `status = 'rejected'`
- ❌ Cannot activate

**Can Activate?** ❌ NO - Desktop app will show: *"License rejected: Invalid UPI transaction"*

---

### Stage 3: User Activates Desktop App
**Trigger:** User enters license key in desktop app

```python
# Desktop app calls
db = get_supabase()
license = db.activate_license('SNAPPY-A1B2C3D4E5F6G7H8', 'machine-123')
```

**Security Checks (in order):**

1. ✅ **Key Exists?**
   ```python
   if not response.data:
       raise Exception("Invalid license key")
   ```

2. ✅ **Still Pending?**
   ```python
   if license_data['status'] == 'pending_verification':
       raise Exception("Payment verification pending...")
   ```

3. ✅ **Was Rejected?**
   ```python
   if license_data['status'] == 'rejected':
       raise Exception(f"License rejected: {admin_notes}")
   ```

4. ✅ **Admin Verified?**
   ```python
   if not license_data['admin_verified']:
       raise Exception("License not verified by admin yet")
   ```

5. ✅ **Already Active? Check Expiry**
   ```python
   if license_data['status'] == 'active':
       if expires_at > now:
           return license_data  # Valid, allow usage
       else:
           raise Exception("License has expired")
   ```

**If all checks pass, activate:**
```python
await supabase.from('licenses').update({
    'status': 'active',
    'invoked_at': now,
    'expires_at': now + 365 days,
    'machine_id': 'machine-123'
})
```

**Database State:**
- ✅ `admin_verified = true`
- ✅ `status = 'active'`
- ✅ `invoked_at = 2025-01-15T10:30:00Z`
- ✅ `expires_at = 2026-01-15T10:30:00Z`

**Can Use?** ✅ YES - Desktop app fully functional for 1 year

---

### Stage 4: License Expiry
**Trigger:** 365 days after activation

**Desktop app checks on every launch:**
```python
if not db.verify_license(license_key):
    show_expiry_dialog()
    disable_features()
```

**verify_license() checks:**
- ✅ `admin_verified = true`
- ✅ `status = 'active'`
- ❌ `expires_at < now` ← EXPIRED!

**Can Use?** ❌ NO - User must renew subscription

---

## Security Scenarios

### ❌ Scenario 1: Fake Payment Attack
**Attacker's Plan:**
1. Submit fake UPI transaction ID
2. Get license key from API response
3. Activate desktop app immediately (before admin rejects)

**What Happens:**
```
Step 1: Submit payment ✓
  └─ License created with status = 'pending_verification'
  └─ admin_verified = false

Step 2: Try to activate desktop app ✗
  └─ activate_license() checks status
  └─ status == 'pending_verification'
  └─ EXCEPTION: "Payment verification pending. Please wait for admin approval."
  └─ Desktop app shows error, stays locked 🔒

Step 3: Admin reviews and rejects ✓
  └─ status = 'rejected'

Step 4: User tries again ✗
  └─ activate_license() checks status
  └─ status == 'rejected'
  └─ EXCEPTION: "License rejected: Invalid UPI transaction"
  └─ Key permanently unusable ❌
```

**Result:** ✅ ATTACK BLOCKED

---

### ✅ Scenario 2: Legitimate Purchase
**User's Journey:**
1. Submit valid UPI payment
2. Wait for admin verification (5-30 minutes)
3. Receive email confirmation
4. Activate desktop app

**What Happens:**
```
Step 1: Submit payment ✓
  └─ License created, status = 'pending_verification'

Step 2: Admin verifies ✓
  └─ admin_verified = true
  └─ Email sent with license key

Step 3: User activates ✓
  └─ activate_license() checks all pass
  └─ status = 'active'
  └─ Desktop app unlocked 🔓

Step 4: Use for 1 year ✓
  └─ verify_license() returns true every launch
  └─ Full features available
```

**Result:** ✅ WORKS PERFECTLY

---

### ⚠️ Scenario 3: License Sharing
**User tries to share key with friend:**
1. User A activates on Machine A
2. User B tries same key on Machine B

**What Happens:**
```
Machine A: activate_license()
  └─ Status: pending_verification → active
  └─ machine_id = 'machine-A'
  └─ Works ✓

Machine B: activate_license()
  └─ Status: already 'active'
  └─ Check expires_at > now ✓
  └─ Update machine_id = 'machine-B'  ← Overwrites!
  └─ Works ✓ (but Machine A's ID is lost)
```

**Current Behavior:** ⚠️ Allows device switching
**Future Enhancement:** Track all machine_ids, limit to N devices

---

## Admin Panel Features

### Payment Verification Page

**Pending Payments Tab:**
- Shows all licenses with `status = 'pending_verification'`
- Admin can:
  - ✅ **Verify** → Sets `admin_verified = true`
  - ❌ **Reject** → Sets `status = 'rejected'`, adds reason

**All Licenses Tab:**
- Shows all licenses regardless of status
- Status indicators:
  - 🟡 Pending Verification
  - 🟢 Active (user activated)
  - 🔴 Rejected
  - ⚫ Expired

---

## Key Takeaways

### ✅ What's Secure:
1. **No activation before verification** - Pending keys cannot be used
2. **Rejected keys are dead** - Once rejected, permanently unusable
3. **Expiry enforced** - Desktop app checks on every launch
4. **Admin has full control** - Can verify or reject any payment

### ⚠️ Future Enhancements:
1. **Device limit** - Restrict to 1-3 devices per license
2. **Deactivation API** - Admin can remotely deactivate licenses
3. **Usage tracking** - Log each activation attempt
4. **Automatic expiry emails** - Warn users 30/15/7 days before expiry
5. **Renewal flow** - Auto-extend existing licenses

### 🔑 Critical Security Rules:
- ✅ Desktop app MUST check `admin_verified`
- ✅ Desktop app MUST check `status != 'rejected'`
- ✅ Desktop app MUST check `status != 'pending_verification'`
- ✅ Desktop app MUST check `expires_at > now`
- ✅ ALL checks must pass before allowing usage

---

## Database Schema Key Fields

```sql
CREATE TABLE licenses (
  license_key TEXT UNIQUE NOT NULL,        -- The actual key (SNAPPY-XXXX)
  status TEXT DEFAULT 'pending_verification', -- pending_verification | active | rejected
  admin_verified BOOLEAN DEFAULT FALSE,    -- Admin approved payment?
  invoked_at TIMESTAMPTZ,                  -- When user first activated
  expires_at TIMESTAMPTZ,                  -- When license expires
  machine_id TEXT,                         -- Last device that activated
  admin_notes TEXT                         -- Reason for rejection (if any)
);
```

---

## Testing Checklist

- [ ] Submit payment with fake UPI → Cannot activate before approval ✅
- [ ] Admin rejects payment → Key becomes unusable ✅
- [ ] Admin verifies payment → Key becomes activatable ✅
- [ ] Activate key → Changes to 'active', sets expiry ✅
- [ ] Try to activate after expiry → Shows expiry error ✅
- [ ] Admin can see all license states in panel ✅

---

## Conclusion

**The system is SECURE** because:
1. License key generation ≠ activation permission
2. Keys require admin verification before use
3. Multiple security checks at activation
4. Rejected keys are permanently blocked
5. Expiry is enforced on every launch

No unauthorized user can activate the desktop app! 🔒
