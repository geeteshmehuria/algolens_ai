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
pnpm test:e2e     # Playwright; requires backend running on :8000, starts :5173 itself
```

### Lint/format

Pre-commit runs ruff + ruff-format on Python. Manually: `pre-commit run --all-files` from the repo root.

## Architecture

### Backend layering

Routers (`app/routers/`) are thin; business logic lives in `app/services/`. All routes are mounted under `/api`. Auth is JWT bearer (`get_current_user` in `routers/auth.py`); content-management endpoints use the `require_admin` dependency (roles: `user`, `admin` in `roles`/`user_roles`).

Key services:

- **`ai_service.py`** — all Gemini calls go through `_generate_json` (JSON mime type, fence-stripping, parse). Raises `AIUnavailableError` (no API key → routers return 503) or `AIGenerationError` (bad response → 502). **Never return fake/placeholder content when AI fails** — honest errors are a deliberate design rule. `ANIMATION_CONTRACTS` defines the per-type step JSON shape.
- **`step_generators.py`** — instrumented real algorithm implementations (binary search, two pointers, stack) that emit animation steps deterministically. The animation endpoint prefers these over Gemini; they must conform to `ANIMATION_CONTRACTS`.
- **`note_service.py`** — AI topic notes: generation is **chunked** (learn/apply/retain + separate quiz) with per-chunk Pydantic validation and retry; never persist a partial note. Notes are versioned rows in `topic_notes` with a draft → published workflow; a partial unique index enforces one published note per topic.
- **`progress_service.py`** — spaced repetition (`REVISION_INTERVALS = [3, 7, 16, 35]` days), streak calculation (**anchored on UTC dates** because `created_on` is `utcnow` — do not use local `date.today()` here), topic proficiency (60% solve rate + 40% avg AI review score), problem recommendations.
- **`email_service.py`** — password reset emails. With `ENVIRONMENT=development` no real mail is sent (links go to logs / dev outbox in `scratch/`).

### Cross-cutting patterns

- **AI responses are cached in the DB, generated once and shared**: per-problem content in `ai_generated_content` (unique on `problem_id, kind`), topic notes in `topic_notes`. First authenticated user may trigger generation; regeneration is admin-only.
- **Attempt side effects**: logging a `Correct` attempt (or passing AI code review) upserts a `revision_queue` entry via `schedule_revision`; completing a revision schedules the next at a growing interval. Dashboard stats (streak, weak topics, recommendations) are computed live from attempts — there are no placeholder values anywhere.
- **Quiz answers never reach the client**: questions live in `topic_quiz_questions` separate from note content; grading is server-side at submit.
- **Animation contract coupling**: step payload keys produced by `step_generators.py`/Gemini must match the per-`animation_type` renderers in `frontend/src/routes/problems/[id]/+page.svelte`. Change both sides together.

### Database / migrations

Alembic owns the schema — there is **no `create_all` at app startup**. Adding/changing models requires a hand-written migration in `backend/migrations/versions/` (revision `0001` is an empty baseline; fresh databases are bootstrapped by `init_db.py` which runs `create_all` then stamps head). Conventions: integer PKs, `VARCHAR` + `CHECK` for statuses (no native PG enums), JSONB for document-shaped content, user-state tables keyed on stable ids (e.g. note progress keys on `topic_id`, not `note_id`, so it survives version bumps).

### Frontend

- Svelte 5 runes syntax (`$state`, `$props`, `$effect`) throughout.
- All API calls go through `src/lib/api.ts` (`api()` attaches the localStorage token, prefixes `/api`, throws `ApiError` carrying FastAPI's `detail`). Base URL overridable via `VITE_API_URL`. Some older pages still use raw `fetch` with hardcoded `http://localhost:8000` — prefer the helper.
- Auth guard lives in `src/routes/+layout.svelte` (localStorage token check + redirect to `/login`); the sidebar nav is defined there too.
- UI primitives in `src/lib/components/ui/` (shadcn-svelte style); feature components for topic notes in `src/lib/components/notes/`.

### Tests

Backend tests use in-memory SQLite via fixtures in `tests/conftest.py` (`session`, `user`, `make_problem` factory) — no Postgres needed. AI-dependent code is tested with mocked Gemini responses. `backend/scratch/` holds throwaway dev scripts, not real tests.

## Environment

`backend/.env` (loaded by `app/config.py`): `DATABASE_URL` (Postgres `algolens_db`), `GOOGLE_GEMINI_API_KEY` (AI endpoints return 503 without it; everything else works), `GEMINI_MODEL`, `ENVIRONMENT`, JWT settings.
