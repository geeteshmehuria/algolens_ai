# AlgoLens AI — Deployment Guide (free tier)

Architecture: **Vercel** (static SvelteKit SPA) → **Render** (FastAPI backend) → **Aiven** (PostgreSQL, already deployed).

All three are usable with **no credit card**. The only trade-off is Render's free
backend sleeps after 15 min idle and cold-starts in ~30–60s on the next request.

---

## 1. Accounts

| Service | URL | Card needed | Purpose |
|---|---|---|---|
| Render | https://render.com | No | FastAPI backend |
| Vercel | https://vercel.com | No | Static frontend |
| GitHub | (existing repo) | No | Source + auto-deploy |
| Aiven | (existing) | No | PostgreSQL (keep) |

Sign in to Render and Vercel **with GitHub** so they can read the repo and auto-deploy.

---

## 2. Environment variables

### Backend (set in Render dashboard — never commit these)
```
DATABASE_URL          = <Aiven URL>?sslmode=require      # secret
JWT_SECRET            = <48+ char random string>          # secret
ENVIRONMENT           = production
FRONTEND_URL          = https://<your-app>.vercel.app
CORS_ORIGINS          = https://<your-app>.vercel.app
GOOGLE_GEMINI_API_KEY = <key>            # optional (AI = 503 without it)
GEMINI_MODEL          = gemini-2.5-flash
RATE_LIMIT_ENABLED    = true
```
Generate the secret:
```
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### Frontend (set in Vercel dashboard — baked in at BUILD time)
```
VITE_API_URL = https://<your-render-service>.onrender.com
```
> Vite inlines this at build. If the backend URL changes, you must **redeploy** the frontend.

---

## 3. Deploy order

### A. Push the deploy-ready code
Make sure `render.yaml`, `frontend/vercel.json`, and any other deploy-config changes are committed and pushed to the branch you'll connect in Render/Vercel (`dev` is fine — select it in both dashboards).

### B. Backend on Render
1. New → **Blueprint** → pick the repo → Render reads `render.yaml`.
   (Or New → Web Service, Root Dir `backend`, Build `pip install -r requirements.txt && alembic upgrade head`, Start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.)
2. Fill the secret env vars from section 2 (leave FRONTEND_URL as a placeholder for now).
3. Deploy. When live, test:
   - `https://<service>.onrender.com/health`  → `{"status":"ok"}`
   - `https://<service>.onrender.com/api/topics` → JSON list (proves DB connection).
4. Copy the backend URL.

### C. Frontend on Vercel
1. Add New → Project → import the repo. Root Directory: `frontend`.
2. Framework Preset: **Other** (or SvelteKit). Build: `pnpm build`. Output: `build`.
3. Env var: `VITE_API_URL = <backend URL>`. Deploy. Copy the Vercel URL.

### D. Wire them together
1. In Render, set `FRONTEND_URL` and `CORS_ORIGINS` to the Vercel URL → save (redeploys).
2. Confirm the frontend's `VITE_API_URL` points at the backend (redeploy frontend if changed).

---

## 4. Post-deploy test checklist
- [ ] `/health` returns ok; `/api/topics` returns data
- [ ] Frontend homepage loads; register + login work
- [ ] Topics list + a notes page load
- [ ] Direct-URL refresh on `/dashboard` works (SPA fallback)
- [ ] No CORS errors / no 500s / no console errors (DevTools)
- [ ] (If Gemini key set) AI generation works and persists after refresh

---

## 5. Risks / things to know
- **Cold start:** free Render backend sleeps after 15 min idle (~30–60s first request).
  Before a demo, open `/health` ~1 min ahead to warm it.
- **DB latency:** put the Render region closest to your Aiven region (`render.yaml` → `region`).
- **SSL:** Aiven requires `?sslmode=require` in `DATABASE_URL`.
- **JWT_SECRET:** the app refuses to boot in production with the default secret.
- **No accidental billing:** none of the chosen tiers require a card.
