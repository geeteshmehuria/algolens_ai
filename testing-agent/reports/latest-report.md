# Full Project Testing & Bug Fix Report

## Summary

- **Date/time:** 2026-06-13 (overnight automated run)
- **Environment tested:** local dev — Windows 11, backend `:8000` (uvicorn --reload), frontend `:5173` (vite), PostgreSQL (Aiven cloud dev DB `defaultdb`)
- **Total checks:** 79 backend tests + 30 Playwright E2E tests + svelte-check (824 files) + production build + schema review + pre-commit hooks
- **Passed:** everything listed above, after fixes
- **Bugs found:** 7 (1 high, 4 medium, 2 low)
- **Fixed:** 7 of 7
- **Remaining issues:** 0 blocking; advisory items listed below

## Bugs Found and Fixed

### 1. Settings page unreachable for some users — HIGH (frontend/auth)
- **File:** `frontend/src/routes/settings/+page.svelte`
- **Problem:** Page required BOTH `token` and `user` in localStorage; the login page stores `user` only best-effort (a failed `/auth/me` during login is swallowed). Affected users were silently bounced /settings → /login → /dashboard.
- **Root cause:** guard checked a cache (`user`) instead of the source of truth (`token` + API).
- **Fix:** page now requires only the token and loads the profile from `GET /api/auth/me`.
- **After fix:** E2E `authed /settings loads clean` passes.

### 2. Settings "Save Changes" was fake — MEDIUM (frontend + backend/API)
- **Files:** `frontend/src/routes/settings/+page.svelte`, `backend/app/routers/auth.py`
- **Problem:** Save was a `setTimeout` writing localStorage and claiming "Settings saved successfully!" — nothing persisted; no profile-update endpoint existed at all.
- **Fix:** new `PUT /api/auth/me` (updates `full_name` / `leetcode_username` only — email/password deliberately excluded); settings page now calls it and shows a real error state on failure.
- **After fix:** 5 new tests in `tests/test_profile_update.py` pass (incl. email-change attempt is ignored; anonymous rejected).

### 3. E2E runs pushed fake addresses through real Gmail SMTP — MEDIUM (backend/email)
- **Files:** `backend/app/services/email_service.py`, `app/config.py`
- **Problem:** after SMTP was configured (previous session), every E2E run sent reset mails for `pw-e2e-*@test.dev` through the real Gmail account → guaranteed bounces, sender-reputation damage; also broke the forgot-password E2E (outbox no longer written).
- **Fix:** in development only, recipients on `EMAIL_DEV_OUTBOX_DOMAINS` (default `test.dev`) route to the dev outbox instead of SMTP. Real addresses still get real email. Production behavior unchanged.
- **After fix:** 2 new routing tests; all 13 forgot/reset E2E tests pass with SMTP configured.

### 4. Hardcoded API URL on problem detail page — MEDIUM (frontend)
- **File:** `frontend/src/routes/problems/[id]/+page.svelte:97`
- **Problem:** raw `fetch('http://localhost:8000/api/...')` bypassed the `api()` helper — breaks under any deployed `VITE_API_URL`, skips central error handling.
- **Fix:** replaced with `api()`; removed dead `token` state.

### 5. Two backend test files lost — MEDIUM (tests)
- **Files:** `backend/tests/test_auth_reset.py`, `backend/tests/test_email_service.py`
- **Problem:** 19 tests (password-reset + email service coverage) were missing from the working tree and were not in commit fbfe874.
- **Fix:** restored in full; all pass.

### 6. Dashboard panels render empty boxes for new users — LOW (UI/UX)
- **File:** `frontend/src/routes/dashboard/+page.svelte`
- **Problem:** "Recommended Next Problems" and "Weak Topics Tracking" had no empty states — brand-new users saw blank cards.
- **Fix:** added `{:else}` empty-state messages to both lists; keyed the recommendations `{#each}`.

### 7. Hot-path foreign keys had no indexes — LOW (database)
- **Files:** `backend/migrations/versions/0005_hot_path_fk_indexes.py`, `app/models.py`
- **Problem:** dashboard stats are computed live from `problem_attempts` (filtered by `user_id`), problems list filters by `topic_id`/`pattern_id`, revision/hints are per-user — none indexed.
- **Fix:** migration `0005` adds 8 indexes (`problem_attempts`, `dsa_problems`, `revision_queue`, `ai_hints`); models updated with `index=True` to stay consistent. Applied to dev DB; non-destructive, reversible via downgrade.

## Bugs Found but Not Fixed

None blocking. Advisory items in Security Notes below.

## UI/UX Issues

- **Pages checked (with screenshots in `testing-agent/reports/screenshots/`):** login, forgot-password, reset-password, dashboard, problems, problem detail, topics, topic notes, revision, roadmap, leetcode-import, settings, admin-as-regular-user, root redirect — at desktop, plus mobile (375px) and tablet (768px) spot checks.
- **Found & fixed:** dashboard empty states (bug 6), settings error display (bug 2).
- **Checked clean:** no horizontal overflow on any tested page/viewport; no console errors; no failed API calls on any authed page; sidebar navigation works end-to-end; `/admin/topic-notes` as non-admin redirects safely to dashboard (no crash, no data leak).

## Backend/API Issues

- **Checked:** all 44 routes enumerated with their auth requirements; startup; OpenAPI; anonymous-rejection on user-scoped endpoints; 403 on all 6 admin endpoints for regular users; full reset-password flow; profile update.
- **Auth map result:** public = catalog reads (`/topics`, `/patterns`, `/problems*`) + auth endpoints; user-JWT = all user-scoped data; admin = content management. Coherent; no endpoint found with missing auth where user data is exposed.
- **Fixed:** bug 2 (missing profile endpoint), bug 3 (email routing).

## Database Issues

- **Checked:** model ↔ live-schema comparison (tables, columns, nullability) — **zero mismatches**; alembic at head (now `0005`); FK index coverage; no plain-text secrets (password bcrypt-hashed, reset tokens stored as SHA-256 only).
- **Fixed:** 8 hot-path indexes (bug 7).
- **Not changed (advisory):** ~15 other FK columns on cold paths (e.g. `topic_notes.created_by`, `leetcode_profile_sync.user_id`) remain unindexed — harmless at current scale; add when those paths get hot.
- **Manual SQL required:** none.

## Security Notes

- Password hashing (bcrypt), token hashing (SHA-256), single-use + 30-min expiry, enumeration-safe responses, and 60s throttle all verified by tests.
- No raw tokens/passwords in logs; dev outbox writes are gated on `ENVIRONMENT=development`.
- **Advisory (unchanged):** problems/topics catalog endpoints are publicly readable — appears intentional (static learning content); flag if you want them auth-gated. JWTs remain valid 24h after a password reset (no server-side session store); add a `token_version` column if reset-should-revoke-sessions matters to you. No rate limiting beyond the reset throttle — recommend `slowapi` before production. `JWT_SECRET` in `.env` is a default-looking value — set a strong unique value in production.

## Commands Run

| Command | Result |
|---|---|
| `pytest tests -q` (multiple runs) | 61 → 79 passed, final **79/79** |
| `pnpm run check` (×3) | 0 errors, 0 warnings |
| `pnpm run build` | success (adapter-auto warning pre-existing) |
| `pnpm exec playwright test` (×3) | final **30/30** |
| `alembic upgrade head` | 0004 → 0005 applied |
| schema/index inspection script | clean (see Database Issues) |
| `pre-commit run --all-files` | all hooks pass |
| E2E test-user cleanup | 12 users + 3 tokens removed; only real user remains |

## Files Changed

| File | Reason |
|---|---|
| `frontend/src/routes/settings/+page.svelte` | real load/save via API, error state (bugs 1, 2) |
| `backend/app/routers/auth.py` | new `PUT /api/auth/me` (bug 2) |
| `frontend/src/routes/problems/[id]/+page.svelte` | use `api()` helper (bug 4) |
| `backend/app/services/email_service.py` | test-domain outbox routing (bug 3) |
| `backend/app/config.py` | `EMAIL_DEV_OUTBOX_DOMAINS` (bug 3) |
| `backend/.env.example` | document new var (bug 3) |
| `frontend/src/routes/dashboard/+page.svelte` | empty states (bug 6) |
| `backend/migrations/versions/0005_hot_path_fk_indexes.py` | new indexes (bug 7) |
| `backend/app/models.py` | `index=True` on hot FKs (bug 7) |
| `backend/tests/test_auth_reset.py` | restored (bug 5) |
| `backend/tests/test_email_service.py` | restored + 2 routing tests (bugs 3, 5) |
| `backend/tests/test_health.py` | new: startup/routes/auth-rejection |
| `backend/tests/test_permissions.py` | new: 403 on all admin endpoints |
| `backend/tests/test_profile_update.py` | new: profile endpoint coverage |
| `frontend/e2e/site-smoke.spec.ts` | new: site-wide E2E (17 tests) |
| `testing-agent/reports/*` | this report + screenshots |

## Final Status

- **Working & verified:** build, type-check, 79 backend tests, 30 E2E tests, all 14 pages load clean at 3 viewports, full auth + password-reset + profile flows, schema consistent at migration head.
- **Not fully verified:** AI generation endpoints (Gemini calls are mocked in tests — live generation not exercised to avoid token spend); LeetCode import flow beyond page load (needs a real LeetCode URL action); real email delivery re-verified only at code level this run (live send confirmed in previous session).
- **Needs manual review:** the four advisory security items above; whether public catalog endpoints should require auth.
- **All changes are uncommitted** — review and commit when ready.
