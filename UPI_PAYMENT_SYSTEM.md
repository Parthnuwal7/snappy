# 🔄 UPI Manual Payment System - Complete Guide

## 📋 Overview

The system has been updated to use **UPI manual payment verification** instead of automatic Razorpay integration. This allows you to:

1. **Users pay via UPI** (scan QR code or use UPI ID)
2. **Users submit transaction ID** for verification
3. **You (Admin) verify payment** in admin panel
4. **You send license email** after manual verification

---

## 🎯 Key Changes Made

### 1. **Razorpay Integration Commented Out**
- All Razorpay code is preserved but commented in `server/index.js`
- Can be re-enabled later if needed
- No Razorpay API keys required now

### 2. **New Database Fields Added**
**licenses table:**
- `payment_method` - 'upi' or 'razorpay'
- `upi_transaction_id` - UPI transaction/UTR number
- `upi_screenshot_path` - Path to payment screenshot (optional)
- `admin_verified` - Boolean flag for admin verification
- `email_sent` - Boolean flag to track if email was sent
- `admin_notes` - Notes from admin
- `verified_at` - Timestamp when admin verified

**payment_logs table:**
- Added same UPI fields for transaction tracking

### 3. **New API Endpoints**

**For Users:**
- `GET /api/payment/upi-details/:plan` - Get UPI QR code and payment info
- `POST /api/payment/submit-upi` - Submit UPI transaction ID

**For Admin:**
- `GET /api/admin/pending-licenses` - Get all pending verifications
- `GET /api/admin/all-licenses` - Get all licenses
- `POST /api/admin/verify-payment/:licenseId` - Verify payment (Step 1)
- `POST /api/admin/send-license-email/:licenseId` - Send email (Step 2)
- `POST /api/admin/reject-payment/:licenseId` - Reject payment

### 4. **New Frontend Components**
- `UPIPaymentModal.tsx` - Payment modal with QR code and transaction ID input
- `AdminPaymentVerification.tsx` - Admin panel for verifying payments

### 5. **Updated Pages**
- **Pricing.tsx** - Now opens UPI payment modal instead of Razorpay
- **App.tsx** - Added `/admin/payments` route

---

## 📥 Setup Instructions

### Step 1: Update Environment Variables

Edit `website/server/.env`:

```env
# Admin Configuration
ADMIN_EMAIL=your-admin-email@gmail.com

# UPI Payment Configuration
UPI_ID=your-upi@paytm

# Comment out Razorpay (already done)
# RAZORPAY_KEY_ID=...
# RAZORPAY_KEY_SECRET=...
```

**Important:** The `ADMIN_EMAIL` is used to identify admin users who can access the verification panel.

### Step 2: Generate UPI QR Codes

Create 3 QR code images in `website/public/qr-codes/`:

1. **starter.png** - QR code for ₹400
2. **pro.png** - QR code for ₹1000
3. **enterprise.png** - QR code for ₹1500

**How to generate QR codes:**

**Option A: Using Payment Apps**
1. Open PhonePe/GPay/Paytm
2. Go to "Request Money" or "QR Code"
3. Generate QR for specific amount
4. Screenshot and save as PNG

**Option B: Online Generator**
1. Visit: https://www.qrcodechimp.com/upi-qr-code-generator
2. Enter your UPI ID
3. Enter amount (400, 1000, or 1500)
4. Download and rename files

### Step 3: Delete Old Database (Important!)

The database schema has changed, so you need to recreate it:

```cmd
cd website\server
del snappy.db
```

The database will be automatically recreated with new fields when you start the server.

### Step 4: Restart Server

```cmd
cd website\server
node index.js
```

---

## 🔄 Complete Payment Flow

### For Users:

1. **User visits Pricing page** (`/pricing`)
2. **Clicks "Get Started"** on any plan
3. **If not logged in:** Redirected to register/login
4. **If logged in:** UPI Payment Modal opens
5. **Modal shows:**
   - QR code for the plan amount
   - UPI ID for manual payment
   - Amount to pay
   - Transaction ID input field
6. **User scans QR code** or pays via UPI ID
7. **User enters UPI Transaction ID** (12-digit UTR number)
8. **User clicks "Submit for Verification"**
9. **Status changes to:** "Pending Verification"
10. **User receives confirmation:** "Payment submitted, will receive email after admin approval"

### For Admin:

#### Step 1: Verify Payment

1. **Navigate to:** `/admin/payments`
2. **See "Pending Verification" tab** with all submitted payments
3. **For each payment, see:**
   - User details (name, email, phone)
   - Plan and amount
   - UPI Transaction ID
   - License key (pre-generated)
   - Submission timestamp
4. **Verify payment** in your bank/UPI app using transaction ID
5. **Click "Verify Payment"** button
6. **Payment moves to** "Verified - Pending Email" tab

#### Step 2: Send License Email

1. **Go to "Verified - Pending Email" tab**
2. **See all verified payments** awaiting email
3. **Click "Send License Email & Activate"**
4. **System sends email** with license key to user
5. **License status changes to** "Active"
6. **User receives email** with:
   - License key (SNAPPY-XXXX-XXXX-XXXX-XXXX)
   - Download link
   - Installation instructions
   - Expiry date (1 year from now)

---

## 🎨 User Interface Changes

### Pricing Page
- **"Get Started" buttons** now open UPI payment modal
- **Modal features:**
  - QR code display
  - Copy UPI ID button
  - Transaction ID input
  - Real-time validation
  - Success/error messages

### Dashboard
- **License status badges:**
  - 🟡 Yellow "Pending Verification" - Awaiting admin approval
  - 🟢 Green "Active" - License activated
  - 🔴 Red "Rejected" - Payment rejected by admin
- **Shows UPI Transaction ID** in license history

### Admin Panel (`/admin/payments`)
- **Two-tab interface:**
  - Tab 1: Pending Verification
  - Tab 2: Verified - Pending Email
- **Quick actions:**
  - Verify payment
  - Reject payment (with reason)
  - Send license email
- **Real-time updates** after each action

---

## 📧 Email Flow (Two-Step Process)

### Email 1: Welcome Email (Automatic)
- **Sent:** When user registers
- **Contains:** Welcome message, link to pricing
- **Automatic:** Yes

### Email 2: License Key Email (Manual Trigger)
- **Sent:** When admin clicks "Send License Email"
- **Contains:**
  - License key
  - Plan details
  - Expiry date (1 year)
  - Download link
  - Installation instructions
- **Manual Trigger:** Yes (admin must click button)

---

## 🔒 Security & Validation

### User-Side Validation:
- ✅ UPI Transaction ID format validation
- ✅ Duplicate transaction ID check
- ✅ Authentication required to submit payment
- ✅ Can't submit payment for same transaction twice

### Admin-Side Protection:
- ✅ Admin authentication required (`ADMIN_EMAIL` check)
- ✅ Can't verify already-verified payments
- ✅ Can't send email twice for same license
- ✅ Can reject payments with reason
- ✅ All actions logged in database

### Database Integrity:
- ✅ Unique constraint on `upi_transaction_id`
- ✅ Foreign key relationships maintained
- ✅ Timestamps for all actions
- ✅ Status tracking (pending_verification, active, rejected)

---

## 🗄️ Database Schema Updates

### licenses Table (New Fields):
```sql
payment_method TEXT DEFAULT 'upi'
upi_transaction_id TEXT
upi_screenshot_path TEXT
admin_verified BOOLEAN DEFAULT 0
email_sent BOOLEAN DEFAULT 0
admin_notes TEXT
verified_at DATETIME
```

### Status Values:
- `pending_verification` - User submitted, awaiting admin
- `active` - Admin verified and email sent
- `rejected` - Admin rejected payment
- `expired` - License expired (after 1 year)

---

## 🧪 Testing the New Flow

### Test as User:

1. Start both servers:
```cmd
REM Terminal 1
cd website\server
node index.js

REM Terminal 2
cd website
npm run dev
```

2. Register a new account
3. Go to Pricing page
4. Click "Get Started" on Starter plan
5. See UPI payment modal
6. Enter a test transaction ID (e.g., `123456789012`)
7. Submit payment
8. Go to Dashboard - should see "Pending Verification" status

### Test as Admin:

1. Make sure your email matches `ADMIN_EMAIL` in `.env`
2. Login with admin account
3. Navigate to `/admin/payments`
4. Should see pending payment from test user
5. Click "Verify Payment"
6. Go to "Verified - Pending Email" tab
7. Click "Send License Email & Activate"
8. Check user's email for license key

---

## ❌ Troubleshooting

### Issue: "Admin access required"
**Solution:** Make sure `ADMIN_EMAIL` in `.env` matches your logged-in user's email

### Issue: QR code not showing
**Solution:** 
1. Check files exist in `website/public/qr-codes/`
2. File names must be: `starter.png`, `pro.png`, `enterprise.png`
3. Restart frontend server after adding images

### Issue: Database errors
**Solution:** Delete `snappy.db` and restart server to recreate with new schema

### Issue: Email not sending
**Solution:** 
1. Verify Gmail app password in `.env`
2. Check you clicked "Send License Email" button (not automatic!)
3. Check spam folder

### Issue: Can't access admin panel
**Solution:** 
1. Login first
2. Your account email must match `ADMIN_EMAIL` in server `.env`
3. Clear browser cache and re-login

---

## 🔄 Re-enabling Razorpay (If Needed)

If you want to switch back to Razorpay later:

1. **Uncomment code in `server/index.js`:**
   - Import statements (lines 5-6)
   - Razorpay initialization (lines 26-29)
   - Payment routes (commented section)

2. **Update frontend:**
   - Uncomment Razorpay methods in `api/client.ts`
   - Create Razorpay checkout component
   - Update Pricing page to use Razorpay

3. **Add Razorpay keys back to `.env`**

---

## 📝 Admin Best Practices

### Before Verifying Payment:
1. ✅ Check transaction ID in your UPI app
2. ✅ Verify amount matches plan price
3. ✅ Verify sender name matches user name
4. ✅ Check transaction date/time is recent

### Before Sending Email:
1. ✅ Confirm payment is actually verified in your bank
2. ✅ Double-check user email is correct
3. ✅ Ensure this is not a duplicate payment

### Rejecting Payments:
- Always provide a clear reason
- Inform user via support email
- Offer refund if payment was legitimate but rejected by mistake

---

## 🎉 Benefits of Manual UPI Verification

### Advantages:
- ✅ **No payment gateway fees** (save 2-3% per transaction)
- ✅ **Direct UPI payments** to your account
- ✅ **Full control** over verification process
- ✅ **No Razorpay account** needed
- ✅ **Flexible pricing** (can offer discounts easily)
- ✅ **Instant settlement** (money directly in your account)

### Considerations:
- ⏰ **Manual work required** (15-30 seconds per payment)
- ⏰ **Not instant** (24-hour verification window)
- 📧 **Two-step email process** (requires admin action)

---

## 🚀 Next Steps

1. **Add UPI QR codes** to `website/public/qr-codes/`
2. **Update `.env`** with your UPI ID and admin email
3. **Delete old database** and restart server
4. **Test complete flow** (user + admin side)
5. **Customize email templates** in `server/email.js` if needed
6. **Set up admin dashboard link** in navigation (optional)

---

## 📞 Support

For any issues with the new UPI payment system:
1. Check this guide first
2. Review console logs (server and browser)
3. Check database for payment status
4. Verify environment variables are set

---

**Status:** ✅ UPI Manual Verification System Complete  
**Razorpay:** 💤 Commented (can be re-enabled)  
**Admin Panel:** ✅ Fully Functional  
**Email System:** ✅ Two-Step Manual Trigger  
**Ready for:** Production Use 🚀
