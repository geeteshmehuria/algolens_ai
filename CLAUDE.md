# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

AlgoLens AI — a DSA learning platform. Monorepo with two apps:

- `backend/` — FastAPI + SQLModel + PostgreSQL + Alembic, Google Gemini integration (`google-genai`)
- `frontend/` — SvelteKit (Svelte 5 runes) + Tailwind CSS 4 + shadcn-style components, package manager is **pnpm** (not npm)

Development happens on Windows; the backend venv lives at `backend\.venv`.

## Commands

### Backend (run from `backend/`)

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000   # dev server (frontend expects :8000)
.venv\Scripts\python.exe -m pytest tests -q                              # all tests
.venv\Scripts\python.exe -m pytest tests/test_progress_service.py::test_streak_broken_by_gap  # single test
.venv\Scripts\python.exe -m alembic upgrade head                         # apply migrations
.venv\Scripts\python.exe -m alembic revision -m "description"            # new migration (hand-written, see below)
.venv\Scripts\python.exe init_db.py                                      # fresh-DB bootstrap: create_all + alembic stamp head + seed
.venv\Scripts\python.exe make_admin.py user@email.com                    # grant admin role
```

### Frontend (run from `frontend/`)

```powershell
pnpm install
pnpm dev          # dev server on :5173
pnpm check        # svelte-check (type checking) — run this after frontend changes
pnpm test:e2e     # all Playwright specs; requires backend running on :8000, starts :5173 itself
pnpm exec playwright test e2e/site-smoke.spec.ts   # single spec
```

### Lint/format

Pre-commit runs ruff + ruff-format on Python plus whitespace/JSON/YAML checks. Manually: `pre-commit run --all-files` from the repo root. `frontend/tsconfig.json` is JSONC and is excluded from the JSON hook.

### Windows server gotcha

`uvicorn --reload` workers are spawned via `multiprocessing` as `C:\Python313\python.exe` (not the venv python). Killing the parent leaves **orphaned workers holding port 8000** that keep serving stale code/env — restarts then silently do nothing. When the backend behaves as if changes (or `.env` edits) aren't applied:

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.Name -match "python" } | Select ProcessId,ParentProcessId,CommandLine
```

and kill any worker whose parent is dead. Note `.env` changes are never hot-reloaded — `--reload` watches `.py` files only; restart the server after editing `.env`.

Related: terminals descended from old conda shells may carry a stale `SSL_CERT_FILE` pointing into the deleted `C:\Users\HP\Miniconda3` — that breaks **every** TLS client in the process (Gemini via httpx, SMTP) with `[Errno 2] No such file or directory`. `app/config.py` runs `_clear_stale_tls_env()` at import to drop TLS override vars whose paths no longer exist (logged as a warning); keep that guard when touching config.

## Architecture

### Backend layering

Routers (`app/routers/`) are thin; business logic lives in `app/services/`. All routes are mounted under `/api`. Auth is JWT bearer (`get_current_user` in `routers/auth.py`); content-management endpoints use the `require_admin` dependency (roles: `user`, `admin` in `roles`/`user_roles`). Catalog reads (`/api/topics`, `/api/problems*`, `/api/patterns`) are deliberately public; all user-scoped data requires the JWT.

Key services:

- **`ai_service.py`** — all Gemini calls go through `_generate_json`: JSON mime type, 90s timeout, retry with backoff (3 attempts) on 429/5xx/timeouts (fail-fast on auth errors), empty/safety-blocked responses raise, and invalid JSON gets exactly **one** correction-prompt retry (bounded token spend). Raises `AIUnavailableError` (no API key → routers return 503 with setup guidance) or `AIGenerationError` (→ 502). **Routers must map these via the local `_ai_error`/`_ai_http_error` helpers** — provider error text can contain internal details, so it goes to the server log while clients get a generic "try again" message. **Never return fake/placeholder content when AI fails** — honest errors are a deliberate design rule. `ANIMATION_CONTRACTS` defines the per-type step JSON shape.
- **`step_generators.py`** — instrumented real algorithm implementations (binary search, two pointers, stack) that emit animation steps deterministically. The animation endpoint prefers these over Gemini; they must conform to `ANIMATION_CONTRACTS`.
- **`note_service.py`** — AI topic notes: generation is **chunked** (learn/apply/retain + separate quiz) with per-chunk Pydantic validation and retry; never persist a partial note. Notes are versioned rows in `topic_notes` with a draft → published workflow; a partial unique index enforces one published note per topic.
- **`progress_service.py`** — spaced repetition (`REVISION_INTERVALS = [3, 7, 16, 35]` days), streak calculation (**anchored on UTC dates** because `created_on` is `utcnow` — do not use local `date.today()` here), topic proficiency (60% solve rate + 40% avg AI review score), problem recommendations.
- **`email_service.py`** — SMTP email (STARTTLS on 587, implicit SSL on 465). Delivery routing: real SMTP when `SMTP_*` settings are present, **except** that in `ENVIRONMENT=development` recipients on `EMAIL_DEV_OUTBOX_DOMAINS` (default `test.dev`) are written to `scratch/dev_outbox.json` instead — this keeps E2E test users from bouncing through the real provider. With no SMTP config: development falls back to the outbox + a stdout print; production raises. **Never log or store raw reset tokens** — logs carry only the recipient.

### Auth and password reset

- Emails are normalized (`strip().lower()`) at register/login/forgot-password and stored lowercase — lookups are exact-match, so never compare against raw user input.
- Passwords are bcrypt; bcrypt 5.x **raises** on >72-byte input, so request schemas validate byte length up front.
- Reset tokens: `secrets.token_urlsafe(32)`, only the SHA-256 stored (`password_reset_tokens`), 30-min expiry, single-use, new request invalidates older unused tokens, 60s per-user issue throttle, generic response regardless of account existence. Reset link is `{FRONTEND_URL}/reset-password?token={raw}`.
- `PUT /api/auth/me` updates `full_name`/`leetcode_username` only — email and password changes are deliberately not supported there.
- Known limitation: JWTs (24h) stay valid after a password reset; there is no server-side revocation.

### Cross-cutting patterns

- **AI responses are cached in the DB, generated once and shared**: per-problem content in `ai_generated_content` (unique on `problem_id, kind`), topic notes in `topic_notes`. First authenticated user may trigger generation; regeneration is admin-only.
- **Attempt side effects**: logging a `Correct` attempt (or passing AI code review) upserts a `revision_queue` entry via `schedule_revision`; completing a revision schedules the next at a growing interval. Dashboard stats (streak, weak topics, recommendations) are computed live from attempts — there are no placeholder values anywhere.
- **Quiz answers never reach the client**: questions live in `topic_quiz_questions` separate from note content; grading is server-side at submit.
- **Animation contract coupling**: step payload keys produced by `step_generators.py`/Gemini must match the per-`animation_type` renderers in `frontend/src/routes/problems/[id]/+page.svelte`. Change both sides together.

### Database / migrations

Alembic owns the schema — there is **no `create_all` at app startup**. Adding/changing models requires a hand-written migration in `backend/migrations/versions/` (revision `0001` is an empty baseline; fresh databases are bootstrapped by `init_db.py` which runs `create_all` then stamps head). Conventions: integer PKs, `VARCHAR` + `CHECK` for statuses (no native PG enums), JSONB for document-shaped content, user-state tables keyed on stable ids (e.g. note progress keys on `topic_id`, not `note_id`, so it survives version bumps). Hot-path FKs are indexed (migration `0005`); keep model `index=True` and migrations in sync.

The dev `DATABASE_URL` points at a **cloud Postgres (Aiven)** — treat it as shared dev data, not disposable.

### Frontend

- Svelte 5 runes syntax (`$state`, `$props`, `$effect`) throughout.
- All API calls go through `src/lib/api.ts` (`api()` attaches the localStorage token, prefixes `/api`, throws `ApiError` carrying FastAPI's `detail`, dedupes in-flight GETs). Base URL overridable via `VITE_API_URL`. Never hardcode `http://localhost:8000` in pages.
- Auth guard lives in `src/routes/+layout.svelte`: a `publicRoutes` list (`/login`, `/forgot-password`, `/reset-password`) renders bare and is exempt from the token redirect — **add any new logged-out page to that list** or it will bounce to /login. The sidebar nav is defined there too.
- `vite.config.ts` ignores `test-results/`, `playwright-report/`, and `e2e/` in the dev watcher — Playwright artifacts written mid-run otherwise trigger reloads that detach the DOM under test.
- UI primitives in `src/lib/components/ui/` (shadcn-svelte style); feature components for topic notes in `src/lib/components/notes/`.

### Tests

- Backend tests use in-memory SQLite via fixtures in `tests/conftest.py` (`session`, `user`, `make_problem` factory) — no Postgres needed. AI-dependent code is tested with mocked Gemini responses; SMTP is tested with a `FakeSMTP` stand-in (no real email from unit tests).
- Playwright specs live in `frontend/e2e/`: `forgot-reset-password.spec.ts` (full reset flow — picks the reset link up from `backend/scratch/dev_outbox.json`) and `site-smoke.spec.ts` (every page × viewports, console errors, failed requests, overflow). E2E test users are `pw-e2e-*@test.dev` with a unique timestamp per run; their domain routes to the dev outbox so no real mail is sent. Clean them from the dev DB by deleting `users` (and their `password_reset_tokens`) where email matches `pw-e2e-%@test.dev`.
- `backend/scratch/` (gitignored) holds throwaway dev scripts — e.g. `send_test_email.py` for live SMTP verification — not real tests.
- `testing-agent/reports/` holds the latest automated test/bug report.

## Environment

`backend/.env` (loaded by `app/config.py`; restart the server after edits): `DATABASE_URL`, `GOOGLE_GEMINI_API_KEY` (AI endpoints return 503 without it; everything else works), `GEMINI_MODEL`, JWT settings, `ENVIRONMENT`, `FRONTEND_URL` + `RESET_TOKEN_EXPIRE_MINUTES` (reset links), `SMTP_HOST/PORT/USERNAME/PASSWORD/FROM_EMAIL/FROM_NAME` (real email; Gmail App Password in dev), `EMAIL_DEV_OUTBOX_DOMAINS`. See `.env.example` for the template.
