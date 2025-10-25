# 🚀 Update Vercel to Use Render Backend

## ✅ Your Backend is Live!

**Render URL**: https://snappy-of4d.onrender.com

**Health Check**: https://snappy-of4d.onrender.com/api/health ✅ Working!

---

## 📝 Update Vercel Environment Variable

### **Method 1: Vercel Dashboard (Recommended)**

1. Go to https://vercel.com/dashboard
2. Select your **snappywebsite** project
3. Go to **Settings** → **Environment Variables**
4. Find `VITE_API_URL` and click **Edit**
5. Change value to:
   ```
   https://snappy-of4d.onrender.com
   ```
   ⚠️ **Important**: No `/api` at the end! Your API routes handle that.
6. Click **Save**
7. Go to **Deployments** tab
8. Click **⋮** on latest deployment → **Redeploy**

---

### **Method 2: Git Push (If you updated .env locally)**

```bash
# This won't work for Vercel - env vars don't come from .env file
# You MUST set them in Vercel dashboard
```

**Note**: Vercel doesn't read `.env` files from your repo. You must set environment variables in the Vercel dashboard.

---

## 🔧 Update Backend CORS

Your backend needs to allow requests from Vercel. Update Render environment variable:

1. Go to https://dashboard.render.com
2. Select **snappy-backend** service
3. Go to **Environment** tab
4. Find `FRONTEND_URL` variable
5. Change value to:
   ```
   https://snappywebsite.vercel.app
   ```
6. Click **Save Changes**
7. Service will auto-redeploy (takes ~1 minute)

---

## ✅ Test Everything

After both updates, test the complete flow:

### 1. **Health Check** (Backend alive)
Visit: https://snappy-of4d.onrender.com/api/health

Should see:
```json
{
  "status": "ok",
  "timestamp": "...",
  "message": "Server is awake and running"
}
```

### 2. **Frontend Wake-Up** (Auto wake on page load)
Visit: https://snappywebsite.vercel.app/

- Open browser console (F12)
- Should see: `✅ Backend is awake`

### 3. **User Registration**
Go to: https://snappywebsite.vercel.app/register

- Register new account
- Should succeed and redirect to login

### 4. **User Login**
Go to: https://snappywebsite.vercel.app/login

- Login with test account
- Should redirect to dashboard

### 5. **Payment Flow**
- Click "Upgrade to Pro"
- Submit UPI payment details
- Should see success message

### 6. **Admin Panel**
Go to: https://snappywebsite.vercel.app/admin/payments

- Login with password: `admin123`
- Should see pending payments
- Verify a payment
- Check if email is sent

### 7. **License Delivery**
- Check user's email inbox
- Should receive license key
- User dashboard should show license (no longer masked)

---

## 🌐 Important URLs

| Service | URL | Purpose |
|---------|-----|---------|
| Frontend | https://snappywebsite.vercel.app | Your website |
| Backend | https://snappy-of4d.onrender.com | API server |
| Health Check | https://snappy-of4d.onrender.com/api/health | Backend status |
| Admin Panel | https://snappywebsite.vercel.app/admin | Payment verification |
| License Manager | https://snappywebsite.vercel.app/admin/licenses | Manage all licenses |
| Supabase | https://zpcjxonzgevcqaidhkwl.supabase.co | Database |

---

## 🔒 Render IP Addresses (For Reference)

Your backend requests come from these IPs (shared with other Render services):

```
44.226.145.213
54.187.200.255
34.213.214.55
35.164.95.156
44.230.95.183
44.229.200.200
74.220.48.0/24
74.220.56.0/24
```

**Use case**: If you need to whitelist Render in external services (e.g., payment gateways, APIs).

---

## ⚠️ Common Issues After Deployment

### CORS Errors
**Symptom**: "Access to fetch at ... has been blocked by CORS policy"

**Fix**:
- Verify `FRONTEND_URL=https://snappywebsite.vercel.app` in Render
- No trailing slash
- Exact match with Vercel domain

### 401 Unauthorized
**Symptom**: Can't login, getting 401 errors

**Fix**:
- Check JWT_SECRET is set correctly in Render
- Check ADMIN_PASSWORD is set correctly in Render

### Email Not Sending
**Symptom**: Payment verified but no email received

**Fix**:
- Check EMAIL_USER and EMAIL_PASS in Render
- Verify Gmail app password is valid
- Check Render logs for email errors

### Backend Sleeping
**Symptom**: First request takes 30+ seconds

**Fix**:
- This is normal on free tier
- Your frontend auto-wakes it up
- Consider upgrading to Starter plan ($7/month) for 24/7 uptime

---

## 📊 Monitor Your Deployment

### Render Dashboard
- **Logs**: https://dashboard.render.com → snappy-backend → Logs
- **Metrics**: CPU, RAM, requests per second
- **Events**: Deployments, crashes, restarts

### Vercel Dashboard
- **Deployments**: https://vercel.com/dashboard → snappywebsite
- **Logs**: Real-time function logs
- **Analytics**: Page views, performance

---

## 🎯 Post-Deployment Checklist

- [ ] Update `VITE_API_URL` in Vercel to `https://snappy-of4d.onrender.com`
- [ ] Update `FRONTEND_URL` in Render to `https://snappywebsite.vercel.app`
- [ ] Redeploy Vercel frontend
- [ ] Test health check endpoint
- [ ] Test user registration
- [ ] Test user login
- [ ] Test payment submission
- [ ] Test admin verification
- [ ] Test email delivery
- [ ] Test license visibility in dashboard
- [ ] Wait 20 minutes → test auto wake-up
- [ ] Run Supabase migration: `fix-license-deletion.sql`
- [ ] Test license deletion from admin panel

---

## 🎉 Done!

Your full-stack application is now live:

✅ Frontend: Vercel  
✅ Backend: Render  
✅ Database: Supabase  
✅ Email: Gmail SMTP  
✅ Auto Wake-Up: Implemented  
✅ Admin Panel: Working  
✅ License Security: Implemented  

**Next Steps:**
1. Update Vercel environment variable
2. Update Render FRONTEND_URL
3. Test everything
4. Go live! 🚀

Questions? Check Render logs or Vercel logs for errors.
