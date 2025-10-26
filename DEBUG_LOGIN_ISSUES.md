# 🔍 Login/Signup Issues - Debug Guide

## What I Just Fixed:

Updated CORS configuration to allow multiple origins:
- ✅ `http://localhost:3000` (local dev)
- ✅ `http://localhost:5173` (Vite dev server)
- ✅ `https://snappywebsite.vercel.app` (production)
- ✅ Dynamic `FRONTEND_URL` from env var

The backend will now log blocked CORS requests with `❌ CORS blocked origin:` in Render logs.

---

## 🚀 Deploy the Fix:

```bash
git add .
git commit -m "Fix CORS to allow Vercel origin"
git push origin main
```

Wait 2-3 minutes for both services to redeploy:
- Vercel: Auto-deploys from main branch
- Render: Auto-deploys when detecting changes

---

## 🔍 Check if CORS is the Issue:

### **1. Open Browser Console (F12)**

Visit: https://snappywebsite.vercel.app/login

Try to login and check the **Console** tab for errors:

**If you see:**
```
Access to fetch at 'https://snappy-of4d.onrender.com/api/auth/login' 
from origin 'https://snappywebsite.vercel.app' has been blocked by CORS policy
```
→ This means CORS is the problem (should be fixed after deploying above changes)

**If you see:**
```
POST https://snappy-of4d.onrender.com/api/auth/login 401 (Unauthorized)
```
→ This means wrong email/password (CORS is working)

**If you see:**
```
POST https://snappy-of4d.onrender.com/api/auth/login 500 (Internal Server Error)
```
→ This means backend error (check Render logs)

---

## 🔍 Check Backend Logs:

1. Go to https://dashboard.render.com
2. Select **snappy-backend** service
3. Click **Logs** tab
4. Try to login from frontend
5. Watch for:
   - `❌ CORS blocked origin:` (CORS issue)
   - `Login error:` (backend error)
   - Database errors

---

## 🧪 Test Backend Directly:

### **Test Health Check:**
```bash
curl https://snappy-of4d.onrender.com/api/health
```

Should return:
```json
{"status":"ok","timestamp":"...","message":"Server is awake and running"}
```

### **Test Login (create test user first):**

Go to: https://snappywebsite.vercel.app/register
- Register with: test@test.com / Test@123

Then test API directly:
```bash
curl -X POST https://snappy-of4d.onrender.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"Test@123"}'
```

Should return:
```json
{"token":"...", "user":{...}}
```

---

## 🔧 Common Issues & Fixes:

### **1. CORS Error**
**Symptom:** Console shows "blocked by CORS policy"

**Fix:**
- ✅ Deploy the updated `index.js` with new CORS config
- ✅ Verify `FRONTEND_URL=https://snappywebsite.vercel.app` in Render
- ✅ No trailing slash in FRONTEND_URL

### **2. 401 Unauthorized**
**Symptom:** Login fails with "Invalid credentials"

**Fix:**
- Check email/password are correct
- Register new account first
- Check if user exists in Supabase `users` table

### **3. 500 Internal Server Error**
**Symptom:** Backend crashes on login

**Fix:**
- Check Render logs for error details
- Verify all env variables are set in Render:
  - JWT_SECRET
  - SUPABASE_URL
  - SUPABASE_KEY
- Check Supabase connection

### **4. Network Error / Cannot Connect**
**Symptom:** "Failed to fetch" or "Network error"

**Fix:**
- Check if backend is awake (visit health check)
- Wait 30 seconds if backend was sleeping
- Check Render service status (should be green)
- Verify `VITE_API_URL=https://snappy-of4d.onrender.com` in Vercel

### **5. Empty Response**
**Symptom:** Login appears to work but nothing happens

**Fix:**
- Check browser console for errors
- Check if token is being stored (Application tab → Local Storage)
- Check frontend `api/client.ts` is using correct URL

---

## 📋 Environment Variables Checklist:

### **Vercel (Frontend):**
- [ ] `VITE_API_URL=https://snappy-of4d.onrender.com`

### **Render (Backend):**
- [ ] `NODE_ENV=production`
- [ ] `PORT=10000`
- [ ] `JWT_SECRET=4a00acdb1f232948870968a7e9c2b7cdc50e58aad614d6b9dc275da7d77fa7ea`
- [ ] `ADMIN_PASSWORD=admin123`
- [ ] `SUPABASE_URL=https://zpcjxonzgevcqaidhkwl.supabase.co`
- [ ] `SUPABASE_KEY=eyJhbGc...` (your anon key)
- [ ] `FRONTEND_URL=https://snappywebsite.vercel.app`
- [ ] `EMAIL_HOST=smtp.gmail.com`
- [ ] `EMAIL_PORT=587`
- [ ] `EMAIL_USER=parthnuwal7@gmail.com`
- [ ] `EMAIL_PASS=exmkevjjikqqndmb`

---

## 🎯 Step-by-Step Debug Process:

1. **Deploy the CORS fix** (push to main branch)
2. **Wait for both services to deploy** (2-3 minutes)
3. **Clear browser cache** (Ctrl+Shift+Delete or Ctrl+F5)
4. **Open browser console** (F12)
5. **Try to login** from https://snappywebsite.vercel.app/login
6. **Check console for errors**
7. **Check Render logs** for backend errors
8. **Report what you see** (exact error message)

---

## 🚨 If Still Not Working:

Share these details:
1. Exact error from browser console
2. Screenshot of Network tab (F12 → Network → filter "login")
3. Render logs from the time you tried to login
4. What URL you're accessing (localhost or Vercel)

---

## ✅ Success Indicators:

After login works, you should see:
- ✅ Console: No CORS errors
- ✅ Network tab: POST /api/auth/login → 200 OK
- ✅ Response: {"token":"...","user":{...}}
- ✅ Redirect to dashboard
- ✅ Dashboard shows user info

---

**Next Step:** Push the CORS fix and test! 🚀
