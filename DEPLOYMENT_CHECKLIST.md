# 📋 Render Deployment Checklist

## ✅ Pre-Deployment (Do this first!)

- [ ] **Email is working locally**
  - Test by verifying a payment and checking if email is sent
  - Run: `npm start` and test on http://localhost:5000

- [ ] **Push code to GitHub**
  ```bash
  git add .
  git commit -m "Ready for Render deployment"
  git push origin master
  ```

- [ ] **Have all env variables ready** (copy from `.env` file)
  - JWT_SECRET
  - ADMIN_PASSWORD
  - SUPABASE_URL
  - SUPABASE_KEY
  - EMAIL_USER
  - EMAIL_PASS

---

## 🚀 Render Setup (10 minutes)

1. [ ] Go to https://render.com → Sign in
2. [ ] Click **New +** → **Web Service**
3. [ ] Connect GitHub repo: `Parthnuwal7/snappy`
4. [ ] Configure service:
   - Name: `snappy-backend`
   - Root Directory: `website/server`
   - Build Command: `npm install`
   - Start Command: `node index.js`
   - Plan: Free (or Starter for no sleep)

5. [ ] Add environment variables (10 variables):
   ```
   NODE_ENV=production
   PORT=5000
   JWT_SECRET=...
   ADMIN_PASSWORD=...
   SUPABASE_URL=...
   SUPABASE_KEY=...
   FRONTEND_URL=https://snappywebsite.vercel.app
   EMAIL_HOST=smtp.gmail.com
   EMAIL_PORT=587
   EMAIL_USER=...
   EMAIL_PASS=...
   ```

6. [ ] Click **Create Web Service**
7. [ ] Wait for deployment (2-5 minutes)
8. [ ] Copy your backend URL (e.g., `https://snappy-backend.onrender.com`)

---

## 🔗 Update Frontend (5 minutes)

1. [ ] Go to https://vercel.com/dashboard
2. [ ] Select `snappywebsite` project
3. [ ] Settings → Environment Variables
4. [ ] Update `VITE_API_URL` to your Render URL
5. [ ] Save and trigger redeploy

---

## ✅ Testing (5 minutes)

Test each endpoint:

1. [ ] **Health check**
   - Visit: `https://your-backend.onrender.com/api/health`
   - Should return: `{"status":"ok",...}`

2. [ ] **User registration**
   - Go to: https://snappywebsite.vercel.app/register
   - Register new account
   - Check for success

3. [ ] **User login**
   - Login with test account
   - Should redirect to dashboard

4. [ ] **Payment flow**
   - Submit UPI payment request
   - Check if appears in admin panel

5. [ ] **Admin panel**
   - Go to: https://snappywebsite.vercel.app/admin/payments
   - Login with ADMIN_PASSWORD
   - Verify a pending payment

6. [ ] **Email sending**
   - After verifying payment, check user's email
   - License key should be received

7. [ ] **Wake-up mechanism**
   - Wait 20 minutes (backend goes to sleep)
   - Visit homepage again
   - Should wake up automatically

---

## 🎯 Post-Deployment

- [ ] **Update documentation** with production URLs
- [ ] **Monitor logs** in Render dashboard for first 24 hours
- [ ] **Test from different devices/networks**
- [ ] **Set up alerts** (optional: Render can notify on failures)

---

## 📊 Important URLs

| Service | URL |
|---------|-----|
| Frontend | https://snappywebsite.vercel.app |
| Backend | https://snappy-backend.onrender.com |
| Health Check | https://snappy-backend.onrender.com/api/health |
| Admin Panel | https://snappywebsite.vercel.app/admin |
| Supabase | https://zpcjxonzgevcqaidhkwl.supabase.co |

---

## 🐛 Common Issues

### ❌ "Cannot connect to backend"
- Check if Render deployment succeeded (green checkmark)
- Check Render logs for errors
- Verify FRONTEND_URL in Render env vars matches Vercel domain

### ❌ CORS errors
- Verify `FRONTEND_URL=https://snappywebsite.vercel.app` (no trailing slash)
- Check browser console for exact CORS error

### ❌ Email not sending
- Check Render logs when clicking "Verify Payment"
- Verify EMAIL_USER and EMAIL_PASS are correct
- Test Gmail app password is still valid

### ❌ Backend sleeping too often
- Normal on free tier (sleeps after 15 min)
- Consider upgrading to Starter plan ($7/month)
- Or keep pinging /api/health every 10 minutes with cron job

---

## 💡 Tips

1. **Free Tier Sleep**: Backend sleeps after 15 min. First request takes ~30s to wake up. Your frontend already handles this!

2. **Logs**: Always check Render logs if something breaks. Most errors are visible there.

3. **Environment Variables**: Double-check all 10 env vars are set correctly. Missing one = broken deployment.

4. **Database**: No need to deploy Supabase - it's already cloud-hosted!

5. **Auto-Deploy**: Render auto-deploys on every `git push` to master. Disable in settings if you want manual control.

---

## 🚀 Ready to Deploy?

**Current Status:**
- ✅ Health check endpoint added (`/api/health`)
- ✅ Frontend wake-up mechanism added (`App.tsx`)
- ✅ Email configured and tested
- ✅ All routes migrated to Supabase
- ✅ Admin panel working
- ✅ License security implemented

**Next Step:** Follow the checklist above! 🎉

Questions? See `RENDER_DEPLOYMENT.md` for detailed guide.
