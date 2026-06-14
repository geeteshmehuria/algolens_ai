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

`config.py` runs `_validate_production_config(settings)` at import: when `ENVIRONMENT` is **not** development/dev/local/test, startup **aborts** if `JWT_SECRET` is the built-in default/empty/<32 chars, or if CORS resolves empty — so the app never serves traffic with forgeable tokens. CORS origins come from `settings.allowed_cors_origins()` (FRONTEND_URL + `CORS_ORIGINS`; localhost added only outside production), not a hardcoded list.

Request bodies are size-bounded at the schema layer (`submitted_code`/notes ≤ 20k chars, names ≤ 150, `hint_level` 1–3, attempt `status` is a `Literal`) to cap cost/DoS and keep DB rows small.

Key services:

- **`ai_service.py`** — all Gemini calls go through `_generate_json`: JSON mime type, 90s timeout, retry with backoff (3 attempts) on 429/5xx/timeouts (fail-fast on auth errors), empty/safety-blocked responses raise, and invalid JSON gets exactly **one** correction-prompt retry (bounded token spend). Raises `AIUnavailableError` (no API key → routers return 503 with setup guidance) or `AIGenerationError` (→ 502). **Routers must map these via the local `_ai_error`/`_ai_http_error` helpers** — provider error text can contain internal details, so it goes to the server log while clients get a generic "try again" message. **Never return fake/placeholder content when AI fails** — honest errors are a deliberate design rule. `ANIMATION_CONTRACTS` defines the per-type step JSON shape.
- **`step_generators.py`** — instrumented real algorithm implementations (binary search, two pointers, stack) that emit animation steps deterministically. The animation endpoint prefers these over Gemini; they must conform to `ANIMATION_CONTRACTS`.
- **`note_service.py`** — AI topic notes: generation is **chunked** (learn/apply/retain + separate quiz) with per-chunk Pydantic validation and retry; never persist a partial note. Notes are versioned rows in `topic_notes` with a draft → published workflow; a partial unique index enforces one published note per topic.
- **`progress_service.py`** — spaced repetition (`REVISION_INTERVALS = [3, 7, 16, 35]` days), streak calculation (**anchored on UTC dates** because `created_on` is `utcnow` — do not use local `date.today()` here), topic proficiency (60% solve rate + 40% avg AI review score), problem recommendations. `learning_summary()` is the single source of the four core counters (solved/attempted/streak/revision-due) reused by both the dashboard summary and `/common/contents` — extend it, don't recompute counts inline. `daily_activity()` returns a dense, zero-filled `[{date,count}]` window (UTC) for the contribution heatmap.
- **`email_service.py`** — SMTP email (STARTTLS on 587, implicit SSL on 465). Delivery routing: real SMTP when `SMTP_*` settings are present, **except** that in `ENVIRONMENT=development` recipients on `EMAIL_DEV_OUTBOX_DOMAINS` (default `test.dev`) are written to `scratch/dev_outbox.json` instead — this keeps E2E test users from bouncing through the real provider. With no SMTP config: development falls back to the outbox + a stdout print; production raises. **Never log or store raw reset tokens** — logs carry only the recipient.
- **`rate_limit.py`** — in-process sliding-window limiter keyed on `(scope, client IP)`, applied as a route `dependencies=[Depends(...)]` to auth (login/register/forgot/reset) and every AI endpoint (`ai.py`, `roadmap.py`). Honors `settings.RATE_LIMIT_ENABLED`. **State is per-process** — behind multiple uvicorn workers the effective limit scales with worker count; a hard global cap needs a proxy/gateway or Redis. Tests reset it via the autouse `_reset_rate_limiter` fixture in `conftest.py`.

`app/common/` (schemas/service/routes, mounted at `/api/common`) is the one place for app-wide bootstrap and lookup data, built to cut repeated calls: `GET /common/contents` (user, roles, permissions, preferences, feature flags, safe `app_config`, `learning_summary`, `version`) is fetched once after login; `GET /common/master-data?keys=topics,patterns,difficulties,languages` returns only the requested lookup lists. Never put secrets, the token, or large lists in `contents`.

### Auth and password reset

- Emails are normalized (`strip().lower()`) at register/login/forgot-password and stored lowercase — lookups are exact-match, so never compare against raw user input.
- Passwords are bcrypt; bcrypt 5.x **raises** on >72-byte input, so request schemas validate byte length up front.
- Reset tokens: `secrets.token_urlsafe(32)`, only the SHA-256 stored (`password_reset_tokens`), 30-min expiry, single-use, new request invalidates older unused tokens, 60s per-user issue throttle, generic response regardless of account existence. Reset link is `{FRONTEND_URL}/reset-password?token={raw}`.
- `PUT /api/auth/me` updates `full_name`/`leetcode_username` only — email and password changes are deliberately not supported there.
- Known limitation: JWTs (24h) stay valid after a password reset; there is no server-side revocation.

### Cross-cutting patterns

- **AI responses are cached in the DB, generated once, never re-called on reopen**: per-problem explanation/animation in `ai_generated_content` (unique on `problem_id, kind`, shared across users), topic notes in `topic_notes`, and **hints cached per `(user, problem, level)` in `ai_hints`**. The solver auto-generates explanation+animation on load (cheap because cached); a per-tab **Regenerate** is the only way to re-spend tokens. Decision on record: keep this shared cache — **do not add a per-user AI-content table.**
- **Attempt side effects & solver restore**: logging a `Correct` attempt (or passing AI code review) upserts a `revision_queue` entry via `schedule_revision`; completing a revision schedules the next at a growing interval. The latest submission's code + review are persisted (`problem_attempts` + `ai_code_reviews`) and rehydrated via `GET /problems/{id}/latest-attempt`, so the editor/review survive refresh and re-login with no extra LLM call. `POST /problems/{id}/run-tests` **does not execute user code** (no sandbox) — it returns sample inputs/expected with `status:"manual"`/`execution_supported:false`; never fabricate pass/fail. Dashboard stats are computed live from attempts — no placeholder values anywhere.
- **Quiz answers never reach the client**: questions live in `topic_quiz_questions` separate from note content; grading is server-side at submit.
- **Animation contract coupling**: step payload keys produced by `step_generators.py`/Gemini must match the per-`animation_type` renderers in `frontend/src/routes/problems/[id]/+page.svelte`. Change both sides together.

### Database / migrations

Alembic owns the schema — there is **no `create_all` at app startup**. Adding/changing models requires a hand-written migration in `backend/migrations/versions/` (revision `0001` is an empty baseline; fresh databases are bootstrapped by `init_db.py` which runs `create_all` then stamps head). Conventions: integer PKs, `VARCHAR` + `CHECK` for statuses (no native PG enums), JSONB for document-shaped content, user-state tables keyed on stable ids (e.g. note progress keys on `topic_id`, not `note_id`, so it survives version bumps). Hot-path FKs are indexed (migration `0005`); keep model `index=True` and migrations in sync.

The dev `DATABASE_URL` points at a **cloud Postgres (Aiven)** — treat it as shared dev data, not disposable.

### Frontend

- Svelte 5 runes syntax (`$state`, `$props`, `$effect`) throughout.
- **Token storage is centralized in `src/lib/auth.ts`** (`getToken`/`setToken`/`getStoredUser`/`setStoredUser`/`clearAuth`/`isAuthenticated`) — never read/write `localStorage` `'token'`/`'user'` directly in pages; route through these so a future HttpOnly-cookie migration is a one-file change. (Bearer JWTs are visible in the Network tab by design; the token is never logged.)
- All API calls go through `src/lib/api.ts` (`api()` attaches the token via `getToken()`, prefixes `/api`, throws `ApiError` carrying FastAPI's `detail`, dedupes in-flight GETs). Base URL overridable via `VITE_API_URL`. Never hardcode `http://localhost:8000` in pages.
- **Common bootstrap/lookup cache: `src/lib/stores/common.ts`** — `loadContents()` (dedupes + caches `/common/contents`; the layout uses it instead of separate `/auth/me` + `/dashboard/summary`) and `loadMasterData(keys)` (caches lookup lists per key across navigations). `clearCommonCache()` is called on logout.
- Auth guard lives in `src/routes/+layout.svelte` and is a **synchronous, no-flash gate**: auth is resolved at first render from `getToken()` and the protected app shell is only mounted when authenticated (logged-out users on a protected route get a neutral splash → `/login`, never a flash of dashboard content). SSR is **off** (`+layout.ts` `ssr=false`), so a server `load` guard can't see the token — the client gate is the correct mechanism. A `publicRoutes` list (`/login`, `/forgot-password`, `/reset-password`) renders bare — **add any new logged-out page to that list** or it bounces to /login. The sidebar nav is defined here too, and `adminOnly` items are hidden unless roles (from `/common/contents`) include `admin`. Hiding nav is UX only — the backend still enforces `require_admin`.
- **Markdown rendering goes through one renderer**: `src/lib/markdown.ts` `renderMarkdown()` (headings, lists, bold/italic, inline + fenced code, GFM tables, links). It is **escape-first** — source is HTML-escaped before any markup is injected — which is why `NoteSection.svelte` can pass the output to `{@html}` safely without a separate sanitizer. Don't add a second markdown path; extend this one. Note `content_md` from AI notes is Markdown, not HTML.
- Topic-notes page (`routes/topics/[topicId]/notes/+page.svelte`) loads notes from a **single `$effect` keyed on `topicId`** (covers direct URL, refresh, back/forward, in-app switch) guarded by a monotonic `loadSeq` so a stale/duplicate response can't strand the spinner — don't reintroduce a parallel `onMount` load.
- `vite.config.ts` ignores `test-results/`, `playwright-report/`, and `e2e/` in the dev watcher — Playwright artifacts written mid-run otherwise trigger reloads that detach the DOM under test.
- UI primitives in `src/lib/components/ui/` (shadcn-svelte style); reusable app-level components (`StatCard`, `DifficultyBadge`, `EmptyState`, `LoadingState`, `AppPageHeader`, `StreakHeatmap`) in `src/lib/components/app/` — prefer these over re-inlining stat tiles / empty/loading blocks; feature components for topic notes in `src/lib/components/notes/`. shadcn's `CardHeader` is a CSS **grid** — inside a flex row give it `flex-1 min-w-0` or its text collapses to one word per line.
- Theme/design tokens live in `src/app.css` (`@theme`): Inter body + Outfit display (`font-title`), brand blue primary, plus `fade-in`/`lift` helpers and a `prefers-reduced-motion` guard. Difficulty colors are emerald/amber/rose; keep new UI on these tokens rather than introducing new palettes.

### Tests

- Backend tests use in-memory SQLite via fixtures in `tests/conftest.py` (`session`, `user`, `make_problem` factory, autouse rate-limit reset) — no Postgres needed. AI-dependent code is tested with mocked Gemini responses; SMTP is tested with a `FakeSMTP` stand-in (no real email from unit tests). `test_security_hardening.py` covers the prod config guard, rate limiting, request-size limits, and pagination.
- `e2e/markdown-render.spec.ts` (unit-style spec for `renderMarkdown`) and `e2e/auth-no-flash.spec.ts` (asserts a logged-out user never sees protected content before the `/login` redirect) are **backend-independent** — runnable with just the dev server. The markdown renderer can also be run directly: `node --experimental-strip-types` against a small TS harness importing `src/lib/markdown.ts`.
- Playwright specs live in `frontend/e2e/`: `forgot-reset-password.spec.ts` (full reset flow — picks the reset link up from `backend/scratch/dev_outbox.json`) and `site-smoke.spec.ts` (every page × viewports, console errors, failed requests, overflow). E2E test users are `pw-e2e-*@test.dev` with a unique timestamp per run; their domain routes to the dev outbox so no real mail is sent. Clean them from the dev DB by deleting `users` (and their `password_reset_tokens`) where email matches `pw-e2e-%@test.dev`.
- `backend/scratch/` (gitignored) holds throwaway dev scripts — e.g. `send_test_email.py` for live SMTP verification — not real tests.
- `testing-agent/reports/` holds the latest automated test/bug report.

## Environment

`backend/.env` (loaded by `app/config.py`; restart the server after edits): `DATABASE_URL`, `GOOGLE_GEMINI_API_KEY` (AI endpoints return 503 without it; everything else works), `GEMINI_MODEL`, `JWT_SECRET` + JWT settings, `ENVIRONMENT`, `FRONTEND_URL` + `RESET_TOKEN_EXPIRE_MINUTES` (reset links), `CORS_ORIGINS` (extra allowed origins), `RATE_LIMIT_ENABLED`, `SMTP_HOST/PORT/USERNAME/PASSWORD/FROM_EMAIL/FROM_NAME` (real email; Gmail App Password in dev), `EMAIL_DEV_OUTBOX_DOMAINS`. See `.env.example` for the template. **Deploying** (`ENVIRONMENT` ≠ development) requires a strong unique `JWT_SECRET` and a real `FRONTEND_URL`/`CORS_ORIGINS`, or startup aborts (see prod config guard above).
