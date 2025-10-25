# 🚀 Deploying Backend to Render.com

## Prerequisites
- GitHub account with this repository pushed
- Render.com account (free tier available)
- All environment variables from `.env` file

---

## 📝 Step-by-Step Deployment

### 1️⃣ **Push Code to GitHub**

If you haven't already:
```bash
git init
git add .
git commit -m "Initial commit - Snappy backend"
git branch -M master
git remote add origin https://github.com/Parthnuwal7/snappy.git
git push -u origin master
```

### 2️⃣ **Create Render Service**

1. Go to https://render.com and sign in
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository: `Parthnuwal7/snappy`
4. Configure the service:

   **Basic Settings:**
   - **Name**: `snappy-backend` (or any name you prefer)
   - **Region**: Singapore (or closest to your users)
   - **Branch**: `master`
   - **Root Directory**: `website/server`
   - **Runtime**: Node
   - **Build Command**: `npm install`
   - **Start Command**: `node index.js`

   **Plan:**
   - Select **Free** (for testing) or **Starter** ($7/month for production)

### 3️⃣ **Add Environment Variables**

In Render dashboard, go to **Environment** tab and add these variables:

```env
NODE_ENV=production
PORT=5000
JWT_SECRET=your-super-secret-jwt-key-at-least-32-chars-long
ADMIN_PASSWORD=admin123
SUPABASE_URL=https://zpcjxonzgevcqaidhkwl.supabase.co
SUPABASE_KEY=your-supabase-anon-key-from-env-file
FRONTEND_URL=https://snappywebsite.vercel.app
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=parthnuwal7@gmail.com
EMAIL_PASS=your-gmail-app-password
```

**Important:** Copy values from your local `website/server/.env` file!

### 4️⃣ **Deploy**

1. Click **"Create Web Service"**
2. Wait for deployment (usually 2-5 minutes)
3. Once deployed, you'll get a URL like: `https://snappy-backend.onrender.com`

### 5️⃣ **Test Your Backend**

Open your browser and visit:
```
https://snappy-backend.onrender.com/api/health
```

You should see:
```json
{
  "status": "ok",
  "timestamp": "2025-10-26T...",
  "message": "Server is awake and running"
}
```

---

## 🔧 Update Frontend to Use Render Backend

### 1️⃣ **Update Vercel Environment Variable**

1. Go to https://vercel.com/dashboard
2. Select your `snappywebsite` project
3. Go to **Settings** → **Environment Variables**
4. Edit `VITE_API_URL` to: `https://snappy-backend.onrender.com`
5. Click **Save**

### 2️⃣ **Redeploy Frontend**

```bash
cd website
git add .
git commit -m "Update API URL to Render backend"
git push
```

Vercel will auto-deploy. Or manually redeploy from Vercel dashboard.

---

## ⚡ Keep Backend Awake (Already Implemented!)

Your frontend now automatically pings `/api/health` when any page loads, which:
- ✅ Wakes up Render if sleeping (free tier sleeps after 15 min inactivity)
- ✅ Ensures fast response times for users
- ✅ No additional configuration needed

### How It Works:
1. User visits any page on `https://snappywebsite.vercel.app/`
2. `App.tsx` calls `wakeUpBackend()` on mount
3. Sends GET request to `/api/health`
4. Render wakes up if sleeping (takes ~30 seconds first time)
5. Subsequent requests are instant

---

## 🎯 Post-Deployment Checklist

- [ ] Backend health check returns 200 OK
- [ ] Frontend can register new users
- [ ] Frontend can login existing users
- [ ] Payment submission works
- [ ] Admin panel accessible
- [ ] Email sending works (verify a payment)
- [ ] License keys appear in user dashboard
- [ ] CORS allows requests from Vercel domain

---

## 🐛 Troubleshooting

### Backend won't start:
- Check **Logs** tab in Render dashboard
- Verify all environment variables are set
- Ensure `JWT_SECRET` is at least 32 characters

### CORS errors:
- Verify `FRONTEND_URL=https://snappywebsite.vercel.app` (no trailing slash)
- Check Render logs for actual error

### Database errors:
- Verify `SUPABASE_URL` and `SUPABASE_KEY` are correct
- Test Supabase connection locally first

### Email not sending:
- Verify `EMAIL_USER` and `EMAIL_PASS` are correct
- Make sure Gmail app password is valid (16 characters, no spaces)
- Check Render logs for email errors

### Free tier sleeping:
- Normal behavior - backend sleeps after 15 min inactivity
- First request after sleep takes ~30 seconds
- Consider upgrading to Starter plan ($7/month) for 24/7 uptime

---

## 💰 Render Free Tier Limits

- ✅ **750 hours/month** (enough for 1 service running 24/7)
- ✅ **Automatic SSL** (HTTPS enabled)
- ✅ **Auto-deploy** from GitHub
- ⚠️ **Sleeps after 15 min** inactivity (wakes on request)
- ⚠️ **Limited CPU/RAM** (sufficient for low-medium traffic)

**Upgrade to Starter ($7/month) for:**
- 🚀 No sleeping (24/7 uptime)
- 🚀 More CPU/RAM
- 🚀 Custom domains

---

## 📊 Monitor Your Deployment

1. **Logs**: Render Dashboard → Logs tab (real-time)
2. **Metrics**: Dashboard → Metrics (CPU, RAM, requests)
3. **Health Check**: Visit `/api/health` anytime

---

## 🔐 Security Notes

1. Never commit `.env` file to GitHub
2. Use strong `JWT_SECRET` (generate with: `node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"`)
3. Change `ADMIN_PASSWORD` from default
4. Enable 2FA on your Render account
5. Regularly update npm packages

---

## 🎉 Done!

Your backend is now live at: `https://snappy-backend.onrender.com`

Test the complete flow:
1. Visit https://snappywebsite.vercel.app/
2. Register → Submit UPI payment → Admin verifies → Email received → License activated

Questions? Check Render logs or revisit this guide! 🚀
