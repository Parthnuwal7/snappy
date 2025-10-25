# 🎓 Admin User Guide - UPI Payment Verification

## 👤 For Administrators Only

This guide is for admins who verify payments and send license keys to users.

---

## 🔐 Accessing the Admin Panel

### Step 1: Make Sure You're an Admin

Your email address must be set as the admin email in the system configuration:

1. Check `website/server/.env` file
2. Look for: `ADMIN_EMAIL=your-admin-email@gmail.com`
3. Make sure it matches your registered account email

### Step 2: Login

1. Go to the website
2. Click **"Login"** in the navbar
3. Enter your email (must match ADMIN_EMAIL)
4. Enter your password
5. Click **"Login"**

### Step 3: Navigate to Admin Panel

**Option A:** Type in browser address bar:
```
http://localhost:3000/admin/payments
```

**Option B:** Bookmark this URL for quick access

---

## 📋 Admin Panel Overview

### Two Tabs:

1. **Pending Verification** (🟡 Yellow)
   - New payments waiting for your verification
   - You need to check these in your bank/UPI app

2. **Verified - Pending Email** (🟢 Green)
   - Payments you've verified
   - Ready to send license email to users

---

## ✅ How to Verify a Payment (Step-by-Step)

### Tab 1: Pending Verification

You'll see a card for each payment with:
- **User Name:** Who made the payment
- **User Email:** Where to send license
- **User Phone:** For contact if needed
- **Plan:** Starter, Pro, or Enterprise
- **Amount:** ₹400, ₹1000, or ₹1500
- **UPI Transaction ID:** 12-digit number from user
- **License Key:** Pre-generated (SNAPPY-XXXX-XXXX-XXXX-XXXX)
- **Submission Time:** When user submitted

### Your Task:

1. **Copy the UPI Transaction ID** from the card
2. **Open your UPI app** (PhonePe, GPay, Paytm, etc.)
3. **Go to transaction history**
4. **Search for the transaction ID**
5. **Verify:**
   - ✅ Transaction exists
   - ✅ Amount matches plan price
   - ✅ Payment status is "Success"
   - ✅ Sender name matches user name (approximately)
   - ✅ Date/time is recent (within 24-48 hours)

6. **If everything checks out:**
   - Click the green **"Verify Payment"** button
   - Confirmation message appears
   - Payment moves to "Verified - Pending Email" tab

7. **If payment is invalid/suspicious:**
   - Click the red **"Reject Payment"** button
   - Enter reason (e.g., "Transaction not found", "Amount mismatch")
   - User's license will be marked as "Rejected"
   - Contact user via support email if needed

---

## 📧 How to Send License Email (Step-by-Step)

### Tab 2: Verified - Pending Email

After you verify a payment, it appears here.

### Your Task:

1. **Double-check** payment is truly verified in your bank
2. **Double-check** user email is correct
3. **Click the blue "Send License Email & Activate" button**
4. **What happens:**
   - System sends email to user with:
     - License key (SNAPPY-XXXX-XXXX-XXXX-XXXX)
     - Plan details
     - Download link
     - Installation instructions
     - Expiry date (1 year from today)
   - License status changes to "Active"
   - Payment disappears from this tab

5. **User receives email within 1-2 minutes**
6. **Done!** User can now use the software

---

## 🚨 Important Rules

### DO:
- ✅ Verify EVERY payment in your UPI app before clicking "Verify"
- ✅ Check transaction ID matches exactly
- ✅ Check amount is correct for the plan
- ✅ Respond to payments within 24 hours
- ✅ Keep track of rejected payments
- ✅ Contact users if you reject their payment

### DON'T:
- ❌ Verify payments without checking your UPI app first
- ❌ Send license emails for unverified payments
- ❌ Share admin login credentials
- ❌ Click "Verify" if you can't find the transaction
- ❌ Send license email twice for same payment (system prevents this)

---

## 📊 Quick Reference Table

| User Action | Admin Action | Email Sent? |
|-------------|--------------|-------------|
| User pays & submits transaction ID | ⏸️ Pending | ❌ No |
| | ✅ Admin verifies payment | ❌ No (not yet) |
| | ✅ Admin sends license email | ✅ Yes! |

---

## 🕐 Daily Admin Routine

### Morning Check (9:00 AM):
1. Login to admin panel
2. Check "Pending Verification" tab
3. Verify all overnight payments
4. Move verified payments to next tab

### Midday Check (2:00 PM):
1. Check "Verified - Pending Email" tab
2. Send license emails to all verified users
3. Check for any new pending payments

### Evening Check (6:00 PM):
1. Final check for pending payments
2. Verify and send emails
3. Check for any support queries related to payments

**Goal:** All payments processed within 24 hours!

---

## 📱 Verifying Payments in Different UPI Apps

### PhonePe:
1. Open PhonePe app
2. Tap "History" at bottom
3. Use search box
4. Paste transaction ID
5. Check transaction details

### Google Pay:
1. Open Google Pay
2. Tap profile icon → "Activity"
3. Use search
4. Paste transaction ID
5. Verify details

### Paytm:
1. Open Paytm
2. Tap "Passbook"
3. Select "UPI" tab
4. Search for transaction ID
5. Check details

### Bank App:
1. Open bank app
2. Go to transaction history
3. Filter by UPI
4. Search for date/amount
5. Match transaction ID

---

## ❓ Common Scenarios

### Scenario 1: Transaction ID Not Found
**What to do:**
1. Check if transaction ID is typed correctly
2. Wait 1-2 hours (sometimes delayed)
3. If still not found after 24 hours, click "Reject"
4. Enter reason: "Transaction not found in bank records"
5. Email user asking them to verify and resubmit

### Scenario 2: Amount Mismatch
**Example:** User paid ₹350 but selected Starter plan (₹400)

**What to do:**
1. Click "Reject Payment"
2. Reason: "Amount mismatch - paid ₹350, required ₹400"
3. Email user explaining the issue
4. Ask user to either:
   - Pay remaining ₹50 and submit new transaction ID
   - Request refund for ₹350

### Scenario 3: Duplicate Transaction ID
**What to do:**
1. Check database - system prevents duplicate IDs
2. If someone tries to reuse, system will block it
3. Ask user to provide correct/new transaction ID

### Scenario 4: User Paid Wrong Amount (More)
**Example:** User paid ₹1000 but selected Starter (₹400)

**What to do:**
**Option A:** Upgrade them to Pro plan
1. Verify payment
2. Update plan to "Pro" in your notes
3. Send Pro plan license email

**Option B:** Refund excess amount
1. Reject payment
2. Process refund for ₹600
3. Ask user to pay ₹400 and resubmit

---

## 🔍 Troubleshooting

### Issue: Can't Access Admin Panel
**Error:** "Admin access required"

**Solution:**
1. Check you're logged in
2. Your email must exactly match ADMIN_EMAIL in server/.env
3. Logout and login again
4. Clear browser cookies

### Issue: Payment Not Showing in Pending Tab
**Possible reasons:**
1. User hasn't submitted yet (check with user)
2. User entered wrong transaction ID
3. Database error (check server console)

**Solution:**
- Ask user to check their dashboard
- Check server logs for errors
- Verify database connection

### Issue: Can't Send Email
**Error:** "Failed to send license email"

**Solution:**
1. Check Gmail configuration in server/.env
2. Verify EMAIL_USER and EMAIL_PASS are correct
3. Check server console for detailed error
4. Test email by registering new user (welcome email should work)

### Issue: Email Sent But User Didn't Receive
**Solution:**
1. Check user's spam/junk folder
2. Verify email address is correct
3. Check server logs for email sending confirmation
4. Resend manually if needed (contact support)

---

## 📈 Admin Statistics to Track

### Daily:
- Number of payments received
- Number of payments verified
- Number of licenses sent
- Number of rejections

### Weekly:
- Total revenue
- Most popular plan
- Average verification time
- Rejection rate

### Monthly:
- Total licenses sold
- Active vs expired licenses
- Customer acquisition trend

---

## 🎯 Pro Tips

1. **Set up notifications:**
   - Bookmark admin panel
   - Check multiple times per day
   - Set phone reminders

2. **Be fast:**
   - Users expect response within 24 hours
   - Faster verification = happier customers

3. **Keep records:**
   - Screenshot suspicious payments
   - Note rejection reasons clearly
   - Track refund requests separately

4. **Communicate:**
   - Email users if you reject payment
   - Explain reason clearly
   - Offer solution (retry, refund, etc.)

5. **Stay organized:**
   - Process payments in order (oldest first)
   - Don't leave verified payments pending email
   - Clear both tabs daily

---

## 📧 Email Templates for Users

### When Rejecting Payment:
```
Subject: Payment Verification Issue - SNAPPY License

Dear [User Name],

We could not verify your payment for SNAPPY [Plan] license.

Reason: [Rejection Reason]

Transaction ID you provided: [Transaction ID]
Amount required: ₹[Amount]

Please:
1. Check the transaction ID is correct
2. Verify payment was successful in your UPI app
3. Resubmit with correct transaction ID

Or contact us at support@snappy.com for assistance.

Best regards,
SNAPPY Support Team
```

### For Duplicate Payments:
```
Subject: Duplicate Payment Detected - SNAPPY License

Dear [User Name],

We noticed you've submitted the same transaction ID twice.

Each transaction ID can only be used once. If you made multiple payments, please provide different transaction IDs for each.

If this was a mistake, please login to your dashboard and check your license status.

Best regards,
SNAPPY Support Team
```

---

## ✅ Success Checklist

Before ending your admin session:

- [ ] All pending payments reviewed
- [ ] All verified payments have emails sent
- [ ] All rejections have reasons documented
- [ ] Any support emails replied to
- [ ] Statistics recorded (optional)

---

## 🆘 Need Help?

**Technical Issues:**
- Check server console logs
- Restart server if needed
- Contact technical support

**Payment Disputes:**
- Document everything
- Keep transaction screenshots
- Email user for clarification
- Process refund if legitimate mistake

**Email Not Working:**
- Check SMTP configuration
- Verify Gmail app password
- Test with welcome email (register new user)

---

## 🎉 You're Ready!

You now know how to:
- ✅ Access the admin panel
- ✅ Verify payments in your UPI app
- ✅ Use the "Verify Payment" button
- ✅ Send license emails to users
- ✅ Reject invalid payments
- ✅ Handle common scenarios
- ✅ Troubleshoot issues

**Remember:** You control the entire payment verification process. Take your time, verify thoroughly, and communicate with users!

---

**Questions?** Refer to `UPI_PAYMENT_SYSTEM.md` for technical details.
