# AlgoLens AI — Security, Performance & AI Import Report

**Date:** 2026-06-14 · **Scope:** pre-deployment audit + fixes · **Branch:** `dev`

## Project
- AlgoLens AI — DSA learning platform (monorepo: `backend/` + `frontend/`).

## Detected stack
- **Frontend:** SvelteKit (Svelte 5 runes) + Tailwind CSS 4 + shadcn-svelte, pnpm.
- **Backend:** FastAPI + SQLModel + Alembic; JWT (pyjwt) + bcrypt; pydantic-settings.
- **Database:** PostgreSQL (Aiven cloud dev); SQLite in tests.
- **AI provider:** Google Gemini (`google-genai`, `gemini-2.5-flash`).

## How "AI questions" actually work here (reality check)
The platform's **problems are admin-curated**, not user-generated. AI generates *explanations,
animations, hints, code reviews, and roadmaps* — already cached once-and-shared in
`ai_generated_content` (unique on `problem_id, kind`) so repeat reads cost **zero** AI tokens.
`POST /problems/import-leetcode-url` is **admin-only** and creates a *placeholder* row (it does
not scrape LeetCode). No "any user generates & stores new questions" subsystem exists, and
building one would be a large unrequested refactor — so this pass **hardens and optimizes the
existing flows** rather than adding a new generation pipeline. (See "Remaining / advisory.")

---

## Security issues found & fixed

| # | Pri | Area | Problem | Risk | Fix | Files | Retest |
|---|-----|------|---------|------|-----|-------|--------|
| 1 | **High** | Config/auth | `JWT_SECRET` fell back to a hardcoded, well-known default if unset | Forgeable tokens incl. **admin** JWTs in prod | Startup guard: non-`development` env aborts if `JWT_SECRET` is the default/empty/<32 chars, or CORS is empty | `app/config.py`, `.env.example` | `import app.config` raises in prod (verified); 5 guard tests pass |
| 2 | **High** | API abuse | No rate limiting on login, register, forgot/reset-password, or AI endpoints | Brute-force + Gemini **cost abuse** | In-process sliding-window limiter applied per-IP to all auth + AI routes | `app/services/rate_limit.py` (new), `routers/auth.py`, `routers/ai.py`, `routers/roadmap.py` | `test_login_is_rate_limited` (11th → 429) passes |
| 3 | **Med** | Input validation | `submitted_code`, notes, names unbounded; `status`/`hint_level` unconstrained | Oversized payload cost/DoS; bad enum data | `max_length` on code (20k), notes (20k), name (150); `Literal` status; `hint_level` 1–3 | `routers/ai.py`, `attempts.py`, `user_problems.py`, `auth.py` | 3 size/enum-rejection tests pass (422) |
| 4 | **Med** | Error hygiene | `roadmap.py` returned raw Gemini error text to clients | Internal detail leak (paths/quotas) | Routed through a generic `_ai_error` like `ai.py`; full detail logged server-side only | `routers/roadmap.py` | reviewed; matches documented rule |
| 5 | **Med** | Deploy/CORS | CORS hardcoded to localhost; no prod origin | Prod frontend blocked; not configurable | `Settings.allowed_cors_origins()` — `FRONTEND_URL` + `CORS_ORIGINS` always; localhost only outside prod | `app/config.py`, `app/main.py`, `.env.example` | `test_dev_cors_*` / prod-origin test pass |

**Checked and judged acceptable (no change):**
- **XSS:** `NoteSection.svelte` uses `{@html}` but HTML-escapes `&`/`<`/`>` *before* applying its
  markdown regex, so AI/user content can't inject tags — low risk, left as-is.
- **Password handling:** bcrypt, >72-byte rejection, normalized emails, SHA-256-only reset tokens,
  single-use + 30-min expiry, enumeration-safe responses — all already solid.
- **Prompt injection:** model output is parsed as strict JSON and rendered as text (no tool use);
  user-controlled code is now length-bounded. Residual risk is low; noted below.

---

## Backend / API optimization

| Problem | Root cause | Fix | Expected improvement |
|---|---|---|---|
| N+1 in `GET /me/bookmarks` | `session.get(DSATopic)` per bookmark | Single `IN` query for all topic names | 1 query instead of N (per bookmark) |
| N+1 in roadmap candidate build | `session.get(DSATopic)` per problem | One `SELECT` of all topics into a dict | 1 query instead of N (per problem) |
| `GET /problems` returned the whole table w/ full descriptions | no pagination/cap | `limit` (default 100, **max 200**) + `offset`, ordered by id | Bounded response size; protects an unauthenticated public endpoint |

**Repeated AI calls:** already prevented by the DB cache (`ai_generated_content`, `topic_notes`,
roadmap rows). The new per-IP AI limiter adds a burst ceiling on *fresh* generation. No change to
the cache-first behavior.

---

## AI question import / generation
- **Previous flow:** admin imports a LeetCode URL → placeholder problem row; AI explanation/animation
  generated on first authenticated request and cached & shared.
- **Problems found:** AI request bodies unbounded (cost); no per-user/IP throttle; roadmap leaked
  provider errors.
- **Improved flow:** request size caps + per-IP AI rate limit + consistent generic AI error mapping.
  Output validation (required-key checks, list coercion, JSON-only with one correction retry) was
  already present in `ai_service.py` and is retained.
- **DB storage:** unchanged & correct — generated content persists in `ai_generated_content` /
  `topic_notes` / `learning_roadmaps` and is reused, never regenerated per page load.

## Database changes
- **Tables checked:** users/roles, problems/solutions/animation steps, attempts/reviews,
  ai_generated_content, hints, bookmarks/notes/progress, revision queue, roadmaps, topic notes/quiz.
- **Migrations added:** none (no schema change needed — fixes are query/validation-level).
- **Indexes:** hot-path FK indexes already added in migration `0005`; no new index required.
- **Data safety:** no destructive operations; shared Aiven dev DB untouched.

## Frontend / UI
- `{@html}` markdown path reviewed and found escape-safe.
- **Fixed:** `/leetcode-import` is admin-only server-side but was shown in the sidebar to every
  logged-in user (dead-end 403 on submit). The layout now loads the user's roles from `/auth/me`
  and hides admin-only nav items; the page itself redirects non-admins to `/dashboard`. Backend
  authorization is unchanged — this is UX only. `pnpm check`: 0 errors / 0 warnings.

## Tests added
| File | Purpose | Result |
|---|---|---|
| `tests/test_security_hardening.py` | prod-config guard (5), rate limiting (2), input-size/enum limits (3), pagination (2) | 12/12 pass |
| `tests/conftest.py` | autouse fixture resetting the rate-limiter between tests | — |

## Commands run
| Command | Result |
|---|---|
| `pytest tests -q` | **108 passed** (was 79; +12 new, rest pre-existing) |
| `pre-commit run ruff` | Passed |
| `pre-commit run ruff-format` | Applied formatting (now clean) |
| `import app.config` with prod env + default secret | RuntimeError (guard works) ✅ |
| `import app.config` with prod env + strong secret | OK; CORS excludes localhost ✅ |

## Files changed
- `backend/app/config.py` — prod config guard, `RATE_LIMIT_ENABLED`, `CORS_ORIGINS`, `allowed_cors_origins()`.
- `backend/app/services/rate_limit.py` — **new** in-process per-IP limiter.
- `backend/app/main.py` — CORS from settings.
- `backend/app/routers/auth.py` — limiters on login/register/forgot/reset; name length cap.
- `backend/app/routers/ai.py` — AI limiter; bounded `submitted_code`/`hint_level`.
- `backend/app/routers/attempts.py` — bounded code + `Literal` status.
- `backend/app/routers/user_problems.py` — bounded note; N+1 fix in bookmarks.
- `backend/app/routers/roadmap.py` — generic AI error mapping; N+1 fix; limiter.
- `backend/app/routers/problems.py` — pagination on `GET /problems`.
- `backend/tests/conftest.py`, `backend/tests/test_security_hardening.py` — limiter reset + new coverage.
- `backend/.env.example` — documented new vars + JWT/prod guidance.
- `frontend/src/routes/+layout.svelte` — load roles, hide admin-only nav items.
- `frontend/src/routes/leetcode-import/+page.svelte` — redirect non-admins.

## Remaining risks / advisory (manual follow-up)
1. **Rate limiter is per-process.** Behind multiple uvicorn workers the effective limit scales with
   worker count. For a hard global cap, add a reverse-proxy/gateway limit or back the limiter with Redis.
2. **JWTs (24h) survive a password reset** — no server-side revocation. Add a `token_version` column
   if reset-should-revoke-sessions matters.
3. **Public catalog endpoints** (`/topics`, `/patterns`, `/problems*`) remain unauthenticated by
   design (static learning content). Gate them if that's not desired.
4. **Prompt-injection residual risk** is low (JSON-only output, no tool use) but inherent to LLM features.
5. **Set real production env** before deploy: strong `JWT_SECRET`, `ENVIRONMENT=production`,
   `FRONTEND_URL`/`CORS_ORIGINS`, working SMTP, `GOOGLE_GEMINI_API_KEY`. The startup guard enforces the first three.

## Deployment readiness
**Not ready until the production `.env` is set** (the guard now enforces this). With a strong
`JWT_SECRET`, `ENVIRONMENT=production`, and a real `FRONTEND_URL`/`CORS_ORIGINS`, the previously
critical auth/abuse gaps are closed and the app is in a deployable posture. No claim of being
"hack-proof" — this removes obvious vulnerabilities and reduces attack surface.
