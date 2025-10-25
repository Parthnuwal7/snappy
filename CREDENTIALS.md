# 🔐 SNAPPY - Test Credentials

## Master Product Key
```
SNAPPY-1782085A3359751C
```
**Valid for:** 10 years (expires: October 24, 2035)

---

## Test Account Credentials

### Option 1: Create New Account
1. Go to: http://localhost:5173/register
2. Use the Master Product Key above
3. Create your own email/password

### Option 2: Use Pre-configured Account
**Email:** `admin@snappy.local`  
**Password:** `Admin@123`  
**Product Key:** `SNAPPY-1782085A3359751C`

---

## Quick Start Guide

### 1. Start Backend
```cmd
cd c:\Users\Lenovo\snappy
run_backend.bat
```

### 2. Start Frontend
```cmd
cd c:\Users\Lenovo\snappy\frontend
npm run dev
```

### 3. Register & Login
1. Open browser: http://localhost:5173
2. Click "Register here"
3. Enter:
   - Email: admin@snappy.local
   - Password: Admin@123
   - Confirm Password: Admin@123
   - Product Key: SNAPPY-1782085A3359751C
4. Click "Create Account"

### 4. Complete Onboarding
Fill in the 3-step onboarding form:

**Step 1: Basic Information**
- Firm Name: Your Law Firm
- Firm Address: 123 Legal Plaza, New Delhi - 110001
- Email: contact@yourfirm.com
- Phone: +91-98765-43210

**Step 2: Banking Details** (Optional but recommended for LAW_001 template)
- Bank Name: State Bank of India
- Account Holder: Your Law Firm
- Account Number: 1234567890
- IFSC Code: SBIN0001234
- UPI ID: yourfirm@oksbi

**Step 3: Preferences**
- Template: LAW_001 (Professional with branding)
- Invoice Prefix: LAW
- Tax Rate: 18.0%
- Currency: INR

### 5. Start Using SNAPPY!
- Create clients
- Generate invoices
- View dashboard & reports
- Manage settings

---

## Features Available After Login

✅ **Dashboard** - Overview of business metrics  
✅ **Invoices** - Create, edit, view, download PDF  
✅ **Clients** - Manage client database  
✅ **Reports** - Analytics and insights  
✅ **Settings** - Firm profile & preferences  

---

## Invoice Templates

### Simple Template
- Minimalist design
- Basic invoice information
- No firm branding

### LAW_001 Template (Professional)
- Yellow header with firm logo
- Complete firm details
- Client billing information
- Itemized services table
- Amount in words
- Bank details & UPI QR code
- Signature section
- Terms & conditions

---

## Testing the Flow

1. **Register** → Enter product key → Create account
2. **Onboarding** → Fill 3-step form → Complete setup
3. **Dashboard** → View overview
4. **Create Client** → Add client details
5. **Create Invoice** → Select client, add items, generate PDF
6. **View Invoice** → Check LAW_001 template with your firm branding
7. **Settings** → Update firm details, change template

---

## Troubleshooting

### Cannot login?
- Make sure backend is running on port 5000
- Check browser console for errors
- Try clearing cookies and re-registering

### Product key invalid?
- Copy the exact key: `SNAPPY-1782085A3359751C`
- Make sure there are no extra spaces
- Key is case-sensitive

### Onboarding not working?
- Firm name and address are required
- Other fields are optional
- Check browser console for errors

---

## File Locations

- **Backend:** `c:\Users\Lenovo\snappy\backend\`
- **Frontend:** `c:\Users\Lenovo\snappy\frontend\`
- **Database:** `c:\Users\Lenovo\snappy\backend\snappy.db`
- **Sessions:** `c:\Users\Lenovo\snappy\backend\flask_session\`

---

## Support

If you encounter any issues:
1. Check both backend and frontend terminals for errors
2. Verify both servers are running (backend: 5000, frontend: 5173)
3. Clear browser cache and cookies
4. Restart both servers

---

🎉 **Enjoy using SNAPPY!**
