# Deployment Guide

This app has two parts:
- **Backend**: Django REST API (Python) — cannot run on Vercel
- **Frontend**: React + Vite (static) — runs on Vercel

## Option A: Frontend on Vercel + Backend on Railway (Recommended)

### 1. Deploy the Django backend to Railway

1. Go to https://railway.app and sign in with GitHub
2. Click **New Project** → **Deploy from GitHub repo**
3. Select `mohammed-sameer-hussain/AI-Career-CoPilot-`
4. Railway will auto-detect Django. If not, set:
   - **Start Command**: `python manage.py runserver 0.0.0.0:$PORT`
   - **Root Directory**: `backend`
5. Add environment variables (in Railway dashboard):
   ```
   DJANGO_SECRET_KEY=<a-long-random-string>
   DJANGO_DEBUG=False
   ALLOWED_HOSTS=.railway.app,localhost,127.0.0.1
   CORS_ALLOWED_ORIGINS=https://your-vercel-app.vercel.app
   OPENAI_API_KEY=<your-key-if-any>
   ```
6. Note the Railway URL, e.g. `https://ai-career-copilot-production.up.railway.app`

### 2. Deploy the React frontend to Vercel

1. Go to https://vercel.com and sign in with GitHub
2. Click **Add New Project** → import `mohammed-sameer-hussain/AI-Career-CoPilot-`
3. Set **Root Directory** to `frontend`
4. **Framework Preset**: Vite
5. **Build Command**: `npm run build`
6. **Output Directory**: `dist`
7. Add **Environment Variable**:
   - Name: `VITE_API_BASE`
   - Value: `https://<your-railway-url>/api`  (e.g. `https://ai-career-copilot-production.up.railway.app/api`)
8. Click **Deploy**

### 3. Update CORS on Railway

After Vercel gives you a URL (e.g. `https://ai-career-copilot.vercel.app`), go back to Railway and set:
```
CORS_ALLOWED_ORIGINS=https://ai-career-copilot.vercel.app
ALLOWED_HOSTS=.railway.app,ai-career-copilot.vercel.app
```

---

## Option B: Full backend+frontend on Render (single URL, simplest)

Render can host Django AND serve the React build from the same origin — just like running locally on `127.0.0.1:8000`.

1. Go to https://render.com → **New Web Service** → connect GitHub repo
2. **Root Directory**: `backend`
3. **Runtime**: Python 3
4. **Build Command**:
   ```
   pip install -r requirements.txt && python manage.py migrate && npm --prefix ../frontend install && npm --prefix ../frontend run build && rm -rf frontend_dist && cp -r ../frontend/dist frontend_dist
   ```
   (On Windows/PowerShell use `xcopy` instead of `cp`.)
5. **Start Command**: `python manage.py runserver 0.0.0.0:$PORT`
6. **Environment Variables**:
   ```
   DJANGO_SECRET_KEY=<random>
   DJANGO_DEBUG=False
   ALLOWED_HOSTS=.onrender.com
   CORS_ALLOWED_ORIGINS=https://your-render-url.onrender.com
   ```
7. Deploy — the app is at `https://your-render-url.onrender.com/`

---

## Option C: Keep it local (no cloud)

Run both servers on your machine:
```cmd
cd backend
python manage.py runserver 127.0.0.1:8000
cd ..\frontend
npm run dev
```
Open http://localhost:5173 (dev) or http://127.0.0.1:8000 (single URL).

---

## Notes
- The database is SQLite by default. For production, switch to PostgreSQL (Railway/Render provide one free).
- File uploads (resumes) go to `media/`. On Railway/Render this is ephemeral — use S3/Cloudinary for permanent storage.
- Never commit `backend/.env` (it is in `.gitignore`).
