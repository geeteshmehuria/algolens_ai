# AlgoLens AI

> An AI-powered Data Structures & Algorithms learning platform — curriculum, topic notes, practice problems, AI explanations/hints/code review, spaced-repetition revision, and progress tracking, all in one place.

![Svelte](https://img.shields.io/badge/SvelteKit-Svelte%205-FF3E00?logo=svelte&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-v4-06B6D4?logo=tailwindcss&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-Frontend-3178C6?logo=typescript&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Aiven-4169E1?logo=postgresql&logoColor=white)
![Gemini](https://img.shields.io/badge/Google_Gemini-AI-8E75B2?logo=googlegemini&logoColor=white)

**Repository:** https://github.com/geeteshmehuria/algolens_ai

---

## Why I Built This

Preparing for DSA interviews is fragmented. Learners bounce between video courses, scattered blog posts, problem sets on one site, and notes in a different app — and none of it talks to each other. Three problems kept recurring:

- **Topics, patterns, notes, and practice live in different places**, so it's hard to see how a concept connects to the problems that test it.
- **Beginners don't get fast, contextual feedback** — they read a solution, but rarely get an explanation tailored to *their* code or a graded check of whether they actually understood the idea.
- **Revision is ad-hoc.** Without a system, you re-solve what you already know and forget what you don't.

**AlgoLens AI** brings the whole loop — *learn → practice → get AI feedback → revise on a schedule* — into a single platform, using Google Gemini to generate structured notes, hints, explanations, and code reviews, with every AI result validated and cached so it's reliable and cheap to reuse.

---

## Project Highlights

- 🧠 **AI-generated topic notes** — chunked (learn / apply / retain) Markdown notes with built-in quizzes, validated and persisted.
- 📚 **Topic-wise DSA curriculum** with patterns, difficulty levels, and a learning roadmap.
- 💻 **Practice problems** with a code editor, sample tests, and per-problem state that survives refresh and re-login.
- 🤖 **AI assistance** — per-problem explanations, step-by-step animations, leveled hints, and code review — all **cached in the database**, generated once, never silently re-billed.
- 🧩 **Automated problem-import pipeline** — curated lists (Blind 75 / Grind 75), AI-generated original practice problems, and optional LeetCode *metadata*, behind an admin review/publish gate.
- 🔁 **Spaced-repetition revision queue** (intervals of 3 / 7 / 16 / 35 days) driven by your attempts.
- 📈 **Progress tracking** — solved/attempted counters, streaks, a contribution heatmap, and topic proficiency.
- 🔐 **Secure auth** — JWT + bcrypt, full password-reset-by-email flow, role-based admin access, rate limiting, and a production config guard.
- 🎨 **Forest-green theme with first-class dark mode** built on Tailwind 4 + shadcn-svelte components.
- ⚙️ **Production deployment config** for Vercel + Render + Aiven (free tier), including health checks and SPA routing.

> **Honesty note:** AlgoLens AI does **not** execute user-submitted code (there is no sandbox). The "Run tests" feature returns sample inputs/expected outputs for manual checking — it never fabricates pass/fail results. This is a deliberate design choice, documented below.

---

## Demo

- **Live Demo:** _Add deployed URL here_ (deploy config for Vercel + Render is included — see [Deployment](#deployment))
- **GitHub Repo:** https://github.com/geeteshmehuria/algolens_ai

### Screenshots

> Forest-green dark theme throughout.

**Login**

<img width="1920" height="1080" alt="login" src="https://github.com/user-attachments/assets/1ae1911e-a264-4fec-90fb-96ec88e05abc" />

**Dashboard** — streak, core counters, weekly activity, and a 12-week contribution heatmap

<img width="1920" height="1080" alt="dashboard" src="https://github.com/user-attachments/assets/8db64f7e-12a6-4510-b656-1597dc9c777a" />


**Practice Problems** — filter by topic/difficulty, with curated-list provenance (Blind 75 / Grind 75)

<img width="1920" height="1080" alt="problems" src="https://github.com/user-attachments/assets/5c91bcbe-4316-479b-a993-e5d9db07bc4e" />


**Topic Notes** — AI-generated study notes across DSA categories, with per-topic progress and quizzes

<img width="1920" height="1080" alt="topic-notes" src="https://github.com/user-attachments/assets/38a37db7-927c-4c61-92e0-8edf8da343d4" />

**Revision Hub** — spaced-repetition queue driven by your attempts

<img width="1920" height="1080" alt="revision" src="https://github.com/user-attachments/assets/a28ce388-1377-46c1-bea3-a9575122e5be" />

**DSA Roadmap** — a structured, AI-generated learning plan

<img width="1920" height="1080" alt="roadmap" src="https://github.com/user-attachments/assets/210d31d6-c584-499d-a4ef-ff1621d41abb" />

**Problem Import (Admin)** — topic-coverage gaps, run import, and a review/publish queue

<img width="1920" height="1080" alt="problem-import" src="https://github.com/user-attachments/assets/a27709dc-80ae-4acc-b195-cf9da7d50489" />

---

## Tech Stack

### Frontend
- **SvelteKit** with **Svelte 5 runes** (`$state`, `$props`, `$effect`)
- **TypeScript**
- **Tailwind CSS v4** (`@theme` design tokens; Inter + Outfit fonts)
- **shadcn-svelte–style components** (built on `bits-ui`, `tailwind-variants`, `clsx`, `tailwind-merge`)
- Static SPA build via `@sveltejs/adapter-static` (SSR off — client-side auth gate)

### Backend
- **FastAPI** (routers thin, business logic in services)
- **SQLModel** (SQLAlchemy + Pydantic) for models and validation
- **Alembic** for hand-written, versioned migrations
- **PyJWT** + **passlib[bcrypt]** for auth
- **google-genai** for Google Gemini integration

### Database
- **PostgreSQL** — local for dev, **Aiven** managed Postgres for the shared cloud dev/prod database
- JSONB for document-shaped content, `VARCHAR + CHECK` for statuses (no native PG enums), integer PKs

### Tooling & Quality
- **pnpm** (frontend package manager), **Vite 8**
- **pytest** (backend, in-memory SQLite fixtures) and **Playwright** (frontend e2e)
- **ruff** + **ruff-format** via **pre-commit**
- **svelte-check** for frontend type checking

---

## Core Features

### 1. DSA Topic Notes
Topic-wise learning with AI-generated notes rendered from Markdown through a single escape-first renderer (`src/lib/markdown.ts`). Notes are generated in chunks (learn / apply / retain) with per-chunk validation, versioned with a draft → published workflow, and never persisted partially. Per-user state (bookmarks, section-read, completion, quiz attempts) is tracked separately so it survives note version bumps. Each note carries a **server-graded quiz** — quiz answers never reach the client.

### 2. Practice Problems
A filterable problem list (topic / difficulty), a problem detail page with a code editor, and per-problem state. The latest submission's code and AI review are persisted and rehydrated on reload via `GET /problems/{id}/latest-attempt`, so your work survives refresh and re-login with no extra AI call.

> **Code execution:** `POST /problems/{id}/run-tests` returns sample inputs and expected outputs with `status: "manual"` (no sandbox executes user code). Pass/fail is never fabricated.

### 3. AI Assistance (Google Gemini)
- **Explanations & animations** — per-problem, auto-generated on first load, then **cached** in `ai_generated_content` (unique per `problem_id, kind`, shared across users).
- **Hints** — leveled (1–3), cached per `(user, problem, level)` in `ai_hints`.
- **Code review** — AI grades a submission; passing a review schedules a revision.
- **Topic notes & quizzes** — chunked generation with Pydantic validation.
- **Problem import** — original, AI-generated practice problems for under-covered topics.

All Gemini calls funnel through one hardened path (`_generate_json`): JSON response mode, 90s timeout, retry-with-backoff on 429/5xx, exactly one correction retry on invalid JSON, and **honest errors** (503/502) instead of placeholder content when AI is unavailable.

### 4. Automated Problem Import
A pipeline (`problem_import/`) that runs *gather → rank → dedup → map-topic → persist → log*, wrapping each source and candidate in try/except so one failure can't abort a run. Sources: **curated lists** (Blind 75 / Grind 75 JSON), **AI-generated** original problems, and an **off-by-default LeetCode metadata** source. Imports land as `review_required` (hidden) and go live only after an admin publishes them. **Legal rule baked in:** only public metadata and AlgoLens-original AI content is stored — never third-party statements, editorials, or premium data.

### 5. User Progress Tracking
- **Streaks** anchored on UTC dates.
- **Spaced-repetition revision queue** with growing intervals (3 / 7 / 16 / 35 days).
- **Contribution heatmap** (`StreakHeatmap`) from a dense, zero-filled daily-activity window.
- **Topic proficiency** = 60% solve rate + 40% average AI review score.
- A single `learning_summary()` source of truth for the four core counters (solved / attempted / streak / revision-due).

### 6. Authentication & Security
- **Register / login** with JWT bearer tokens (24h) and bcrypt password hashing.
- **Full password reset by email** — single-use SHA-256-stored tokens, 30-min expiry, per-user throttle, generic responses regardless of account existence.
- **Role-based access** (`user` / `admin`); admin-only content management behind a `require_admin` dependency.
- **Production config guard** — the app refuses to start in production with a default/weak `JWT_SECRET` or empty CORS.
- **Rate limiting** on auth and all AI endpoints.

### 7. UI / UX
- **Forest-green theme** with first-class **dark mode** and a `prefers-reduced-motion` guard.
- Responsive layout with reusable app components (`StatCard`, `DifficultyBadge`, `EmptyState`, `LoadingState`, `AppPageHeader`, `StreakHeatmap`).
- A **synchronous, no-flash auth gate** — logged-out users never see protected content before redirecting to `/login`.

---

## Architecture Overview

```mermaid
flowchart TD
    User[User Browser] --> Frontend[SvelteKit SPA<br/>Svelte 5 + Tailwind 4]
    Frontend -->|REST /api, JWT bearer| API[FastAPI Backend]
    API --> DB[(PostgreSQL / Aiven)]
    API -->|google-genai| AI[Google Gemini API]
    Cron[External Scheduler] -->|daily_import job| API
```

- The **frontend** is a static SPA. Every request goes through one API client (`src/lib/api.ts`) that attaches the JWT, prefixes `/api`, and dedupes in-flight GETs.
- The **backend** handles auth, validation, AI orchestration, and persistence. Routers are thin; logic lives in `app/services/`.
- The **database** is the source of truth and the **AI cache** — explanations, notes, hints, and reviews are generated once and reused.
- The **daily import** runs as a **standalone job** (`app/jobs/daily_import.py`) invoked by an external scheduler — *not* in-process, because `uvicorn --reload` spawns multiple workers that would each fire the timer and duplicate imports.

---

## Folder Structure

```text
algolens_ai/
├── backend/
│   ├── app/
│   │   ├── routers/        # thin HTTP layer (auth, problems, ai, topic_notes, ...)
│   │   ├── services/       # business logic (ai_service, note_service, progress_service, ...)
│   │   │   └── problem_import/   # gather → rank → dedup → map → persist pipeline
│   │   ├── common/         # app-wide bootstrap + lookup endpoints
│   │   ├── jobs/           # daily_import (external cron entrypoint)
│   │   ├── seed/           # curriculum + curated_lists (blind75.json, grind75.json)
│   │   ├── models.py       # SQLModel tables
│   │   ├── config.py       # settings + production config guard
│   │   └── main.py         # FastAPI app, routers, /health
│   ├── migrations/         # Alembic (hand-written, versioned)
│   ├── tests/              # pytest (in-memory SQLite)
│   ├── requirements.txt
│   └── init_db.py          # fresh-DB bootstrap (create_all + stamp + seed)
├── frontend/
│   ├── src/
│   │   ├── routes/         # dashboard, topics, problems, revision, roadmap, admin, ...
│   │   └── lib/            # api.ts, auth.ts, stores/, components/ (ui + app + notes)
│   ├── e2e/                # Playwright specs
│   └── package.json
├── render.yaml             # Render blueprint (backend)
├── DEPLOYMENT.md           # Vercel + Render + Aiven deploy guide
└── README.md
```

---

## Database Design Summary

Alembic owns the schema (no `create_all` at startup). Key areas (25 tables):

| Area | Tables |
|---|---|
| **Users & auth** | `users`, `roles`, `user_roles`, `password_reset_tokens` |
| **Curriculum** | `dsa_topics`, `dsa_patterns`, `learning_roadmap` |
| **Problems** | `dsa_problems`, `problem_solutions`, `problem_animation_steps` |
| **Practice & review** | `problem_attempts`, `ai_code_reviews`, `revision_queue`, `user_problem_progress` |
| **AI content (cache)** | `ai_generated_content`, `ai_hints`, `ai_note_generation_logs` |
| **Topic notes** | `topic_notes`, `topic_quiz_questions`, `user_quiz_attempts`, `user_topic_note_state` |
| **User data** | `user_bookmarks`, `user_notes`, `leetcode_profile_sync` |
| **Import provenance** | `problem_import_runs` (+ provenance columns & a partial unique index on `dsa_problems`) |

Conventions: integer PKs, `VARCHAR + CHECK` for statuses, JSONB for document-shaped content, and user-state tables keyed on stable IDs (e.g. note progress keys on `topic_id`, not `note_id`, so it survives version bumps). Hot-path FKs are indexed.

---

## AI Workflow

1. A user opens a problem / requests notes / submits code for review.
2. The router validates the request (size-bounded schemas) and checks the **DB cache** first.
3. On a cache miss, the backend calls **Gemini** through the hardened `_generate_json` helper (JSON mode, timeout, retries).
4. The response is **validated** (Pydantic / contract checks); invalid JSON gets exactly one correction retry.
5. The validated result is **persisted** (`ai_generated_content`, `ai_hints`, `topic_notes`, ...) so it's reused for free on reopen.
6. The frontend renders the structured output (Markdown notes, animation steps, hints, review).

If AI is unavailable, the API returns an honest **503/502** — never fake content. Re-spending tokens requires an explicit per-tab **Regenerate**.

---

## Security Considerations

- **Secrets in environment variables only** — `DATABASE_URL`, `JWT_SECRET`, and `GOOGLE_GEMINI_API_KEY` use Render's `sync: false` and are never committed.
- **JWT bearer auth** with bcrypt hashing; request schemas validate password byte-length (bcrypt 5.x raises on >72 bytes).
- **Protected routes** — user-scoped data requires a valid JWT; admin actions require the `require_admin` role dependency (the backend enforces it even though nav is hidden client-side).
- **Production config guard** aborts startup with a weak `JWT_SECRET` or empty CORS.
- **Input validation & size limits** at the schema layer to cap cost/DoS.
- **AI output validation** before anything is stored or rendered.
- **CORS** is config-driven (`FRONTEND_URL` + `CORS_ORIGINS`), not a hardcoded list.
- **Password-reset tokens** store only a SHA-256 hash; raw tokens are never logged.
- **Rate limiting** on auth and AI endpoints.

> This is a learning/portfolio project, not a security-audited product. Known limitation: JWTs remain valid for their lifetime after a password reset (no server-side revocation).

---

## Getting Started

### Prerequisites
- **Node.js** + **pnpm**
- **Python 3.13** (or **uv** package manager)
- **PostgreSQL** (local) or an Aiven Postgres URL

### Backend (run from `backend/`)

#### Option A: Using `uv` (Recommended)
```powershell
# configure environment
copy .env.example .env        # then edit values (DATABASE_URL, JWT_SECRET, ...)

# bootstrap a fresh database (create tables, stamp Alembic head, seed curriculum)
uv run init_db.py
# or, against an existing DB, apply migrations:
uv run alembic upgrade head

# run the dev server (frontend expects :8000)
uv run uvicorn app.main:app --reload --port 8000
```

#### Option B: Standard Python `venv`
```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt

# configure environment
copy .env.example .env        # then edit values (DATABASE_URL, JWT_SECRET, ...)

# bootstrap a fresh database (create tables, stamp Alembic head, seed curriculum)
.venv\Scripts\python.exe init_db.py
# or, against an existing DB, apply migrations:
.venv\Scripts\python.exe -m alembic upgrade head

# run the dev server (frontend expects :8000)
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

> AI endpoints return **503** without `GOOGLE_GEMINI_API_KEY` — everything else works without a key.

### Frontend (run from `frontend/`)

```powershell
pnpm install
pnpm run dev          # dev server on :5173
```

The frontend calls `http://localhost:8000` by default; override with `VITE_API_URL`.

---

## Environment Variables

### Backend (`backend/.env` — see `.env.example`)

```env
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/algolens_db

# Auth
JWT_SECRET=your_jwt_secret_key_here      # strong & unique in production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Environment & CORS
ENVIRONMENT=development                   # non-dev triggers the prod config guard
FRONTEND_URL=http://localhost:5173        # also used to build reset links
CORS_ORIGINS=                             # extra allowed origins (comma-separated)
RATE_LIMIT_ENABLED=true

# Password reset email (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your@gmail.com
SMTP_PASSWORD=your_16_char_app_password
SMTP_FROM_NAME=AlgoLens AI
EMAIL_DEV_OUTBOX_DOMAINS=test.dev

# AI (Google Gemini)
GOOGLE_GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash

# Problem import pipeline
PROBLEM_IMPORT_DAILY_LIMIT=10
PROBLEM_IMPORT_AI_ENABLED=true
PROBLEM_IMPORT_LEETCODE_ENABLED=false     # off by default (legal grey area)
```

### Frontend (`frontend/.env` — see `frontend/.env.example`)

```env
VITE_API_URL=http://localhost:8000        # baked in at build time
```

---

## Running Tests

### Backend (pytest, in-memory SQLite — no Postgres needed)

Using `uv`:
```powershell
uv run pytest tests -q
```

Using standard `venv`:
```powershell
.venv\Scripts\python.exe -m pytest tests -q
```

### Frontend type check + e2e (Playwright)

```powershell
pnpm check        # svelte-check type checking
pnpm test:e2e     # Playwright specs (needs backend on :8000; starts :5173 itself)
```

Some specs (`markdown-render`, `auth-no-flash`) are backend-independent. `test_security_hardening.py` covers the prod config guard, rate limiting, request-size limits, and pagination.

---

## Deployment

A free-tier deployment is fully configured (see [`DEPLOYMENT.md`](DEPLOYMENT.md)):

| Layer | Provider | Notes |
|---|---|---|
| **Database** | Aiven PostgreSQL | requires `?sslmode=require` |
| **Backend** | Render (`render.yaml` blueprint) | `/health` probe; secrets via `sync: false` |
| **Frontend** | Vercel (static SPA) | SPA fallback via `vercel.json`; `VITE_API_URL` baked at build |

Build/run commands, env-var setup, deploy order, and a post-deploy checklist are documented in `DEPLOYMENT.md`. (Note: Render free tier sleeps after 15 min idle and cold-starts in ~30–60s.)

---

## What I Learned

- **Full-stack architecture** across a SvelteKit SPA and a layered FastAPI backend.
- **API design** with a thin-router / service-layer split and a single bootstrap endpoint (`/common/contents`) to cut redundant round-trips.
- **Database modeling & migrations** — hand-written Alembic migrations, partial unique indexes, and user-state tables keyed for forward compatibility.
- **Safe AI integration** — schema-validated structured output, bounded retries, honest error handling, and a DB cache so the same content is never billed twice.
- **Auth & security** — JWT/bcrypt, an email password-reset flow, a production config guard, and rate limiting.
- **UI/UX engineering** — Svelte 5 runes, Tailwind 4 design tokens, a no-flash auth gate, and an escape-first Markdown renderer.
- **Cost & performance optimization** — caching AI responses, deduping in-flight GETs, and computing dashboard stats from a single source of truth.

---

## Roadmap

- Real code execution / test runner (sandboxed) to replace the manual sample-test flow
- More DSA topics and curated problem sets
- Richer analytics (time-on-task, weak-area breakdowns)
- Company-wise interview preparation tracks
- Server-side JWT revocation after password reset
- CI/CD pipeline and automated QA gates

---

## Interview Talking Points

- **Not a CRUD app:** it orchestrates an external LLM safely (validation, retries, honest failure), caches results in a relational schema, and runs a multi-stage import pipeline behind an admin review gate.
- **AI is integrated defensively:** one hardened call path, JSON-mode + bounded retries, and a strict rule never to return placeholder content on failure.
- **Generated content is persisted and reused:** explanations/animations are unique per problem and shared across users; hints are cached per `(user, problem, level)` — re-spending tokens is an explicit user action.
- **Progress tracking is real, not faked:** streaks and a spaced-repetition queue derive from actual attempts, with one `learning_summary()` source of truth.
- **Frontend ↔ backend contract:** a single API client attaches the JWT and dedupes GETs; a static SPA with a synchronous client-side auth gate (SSR off) avoids any flash of protected content.
- **Schema decisions:** integer PKs, `CHECK`-constrained statuses, JSONB for documents, indexed hot-path FKs, and migrations kept in lockstep with models.
- **Optimizations:** DB-level AI caching, request dedup, and a consolidated bootstrap endpoint.
- **What I'd improve next:** a real sandboxed code runner and JWT revocation (see Roadmap).
- **A principled trade-off I can defend:** AlgoLens AI imports only public metadata + original AI content — never third-party problem statements or premium data.

---

## Author

**Built by Geetesh Maihuria**
GitHub: https://github.com/geeteshmehuria
