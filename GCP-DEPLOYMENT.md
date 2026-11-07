# AlgoLens AI — GCP Deployment Guide

**Architecture:**
- **Cloud Run** (FastAPI backend, Docker) → free tier: 2M req/month, 360k GB-sec/month
- **Firebase Hosting** (static SvelteKit SPA) → free tier: 10 GB bandwidth/month
- **Neon** (PostgreSQL, serverless) → free at neon.tech, no card needed

No credit card required for the free tiers above.

---

## Prerequisites

Install these tools once:

```bash
gcloud --version
```

```bash
npm install -g firebase-tools
```

```bash
firebase --version
```

Download gcloud CLI: https://cloud.google.com/sdk/docs/install

---

## 1. One-time GCP project setup

Log in:
```bash
gcloud auth login
```

Create a project (skip if reusing an existing one):
```bash
gcloud projects create algolens-ai --name="AlgoLens AI"
```

```bash
gcloud config set project algolens-ai
```

Enable required APIs:
```bash
gcloud services enable run.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com cloudbuild.googleapis.com
```

---

## 2. Store secrets in Secret Manager

Generate a strong JWT secret (run this, copy the output):
```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Create each secret — replace the value inside the quotes before running:

```bash
echo -n "postgresql://user:pass@ep-xxx.region.aws.neon.tech/neondb?sslmode=require" | gcloud secrets create DATABASE_URL --data-file=-
```

```bash
echo -n "paste_jwt_secret_here" | gcloud secrets create JWT_SECRET --data-file=-
```

```bash
echo -n "https://algolens-ai.web.app" | gcloud secrets create FRONTEND_URL --data-file=-
```

```bash
echo -n "https://algolens-ai.web.app" | gcloud secrets create CORS_ORIGINS --data-file=-
```

```bash
echo -n "paste_gemini_api_key_here" | gcloud secrets create GOOGLE_GEMINI_API_KEY --data-file=-
```

SMTP secrets (needed for password-reset emails — Gmail App Password: https://myaccount.google.com/apppasswords):

```bash
echo -n "smtp.gmail.com" | gcloud secrets create SMTP_HOST --data-file=-
```

```bash
echo -n "587" | gcloud secrets create SMTP_PORT --data-file=-
```

```bash
echo -n "you@gmail.com" | gcloud secrets create SMTP_USERNAME --data-file=-
```

```bash
echo -n "your_16_char_app_password" | gcloud secrets create SMTP_PASSWORD --data-file=-
```

```bash
echo -n "you@gmail.com" | gcloud secrets create SMTP_FROM_EMAIL --data-file=-
```

---

## 3. Build & deploy the backend (Cloud Run)

Go into the backend folder:
```bash
cd backend
```

Build and push the Docker image (no local Docker needed — Cloud Build does it):
```bash
gcloud builds submit --tag gcr.io/algolens-ai/algolens-backend .
```

Deploy to Cloud Run:
```bash
gcloud run deploy algolens-backend --image gcr.io/algolens-ai/algolens-backend --platform managed --region asia-south1 --allow-unauthenticated --port 8080 --min-instances 0 --max-instances 3 --set-env-vars "ENVIRONMENT=production,RATE_LIMIT_ENABLED=true,GEMINI_MODEL=gemini-2.5-flash" --set-secrets "DATABASE_URL=DATABASE_URL:latest,JWT_SECRET=JWT_SECRET:latest,FRONTEND_URL=FRONTEND_URL:latest,CORS_ORIGINS=CORS_ORIGINS:latest,GOOGLE_GEMINI_API_KEY=GOOGLE_GEMINI_API_KEY:latest,SMTP_HOST=SMTP_HOST:latest,SMTP_PORT=SMTP_PORT:latest,SMTP_USERNAME=SMTP_USERNAME:latest,SMTP_PASSWORD=SMTP_PASSWORD:latest,SMTP_FROM_EMAIL=SMTP_FROM_EMAIL:latest"
```

Cloud Run will print the backend URL, e.g. `https://algolens-backend-xxxx-as.a.run.app`

Test it (replace with your actual URL):
```bash
curl https://algolens-backend-xxxx-as.a.run.app/health
```

```bash
curl https://algolens-backend-xxxx-as.a.run.app/api/topics
```

---

## 4. Update FRONTEND_URL secret

After the Firebase deploy in step 5 you'll know your Firebase URL. Update the secret and redeploy the backend:

```bash
echo -n "https://algolens-ai.web.app" | gcloud secrets versions add FRONTEND_URL --data-file=-
```

```bash
echo -n "https://algolens-ai.web.app" | gcloud secrets versions add CORS_ORIGINS --data-file=-
```

```bash
gcloud run deploy algolens-backend --image gcr.io/algolens-ai/algolens-backend --region asia-south1 --platform managed
```

---

## 5. Deploy the frontend (Firebase Hosting)

Go into the frontend folder:
```bash
cd frontend
```

Log in to Firebase:
```bash
firebase login
```

> Edit `.firebaserc` at the repo root — replace `YOUR_FIREBASE_PROJECT_ID` with `algolens-ai`

Build with the backend URL baked in (replace the URL with yours from step 3):
```bash
VITE_API_URL=https://algolens-backend-xxxx-as.a.run.app pnpm build
```

Deploy:
```bash
firebase deploy --only hosting
```

> **Note:** `VITE_API_URL` is baked into the static bundle at build time. If the backend URL ever changes, rebuild and redeploy the frontend.

---

## 6. Post-deploy checklist

- [ ] `/health` returns `{"status":"ok"}`
- [ ] `/api/topics` returns a list (DB connected)
- [ ] Frontend homepage loads
- [ ] Register + login works
- [ ] Topics list and a notes page load
- [ ] Direct-URL refresh (e.g. `/dashboard`) works (SPA fallback)
- [ ] No CORS errors in browser DevTools
- [ ] (If Gemini key set) AI generation works and persists after refresh

---

## 7. Re-deploying after code changes

Backend only — build then deploy:
```bash
gcloud builds submit --tag gcr.io/algolens-ai/algolens-backend ./backend
```

```bash
gcloud run deploy algolens-backend --image gcr.io/algolens-ai/algolens-backend --region asia-south1 --platform managed
```

Frontend only — build then deploy (replace URL with yours):
```bash
VITE_API_URL=https://algolens-backend-xxxx-as.a.run.app pnpm build
```

```bash
firebase deploy --only hosting
```

---

## 8. Things to know

| Topic | Detail |
|---|---|
| **Cold starts** | Cloud Run scales to zero when idle; first request after a gap takes ~2–5s. Set `--min-instances 1` to avoid this (uses more free quota). |
| **Free tier limits** | Cloud Run: 2M requests/month, 360k GB-sec/month CPU-time. Firebase Hosting: 10 GB bandwidth/month. Both are generous for a portfolio project. |
| **Alembic migrations** | The Dockerfile runs `alembic upgrade head` before starting uvicorn. If a migration fails the container exits — check Cloud Run logs. |
| **Rate limiting** | `rate_limit.py` is per-process; with `--max-instances > 1` the effective limit scales. For a hard cap, set `--max-instances 1` or add a Cloud Armor policy. |
| **Updating a secret** | `gcloud secrets versions add SECRET_NAME --data-file=-` then redeploy Cloud Run. |
| **Region** | `asia-south1` (Mumbai) is closest to most South/Southeast Asian users. Change to `us-central1` for a US audience. |
| **Custom domain** | Firebase Hosting → "Add custom domain" in Firebase Console (free SSL). Cloud Run → "Domain mappings" in Cloud Run console (also free). |
