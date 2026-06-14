# AlgoLens Topic Notes Fix Report

**Target page:** `/topics/2/notes` · **Date:** 2026-06-14

## Root causes found

- **Direct URL loading:** The page loaded notes from **two** triggers — `onMount`
  (`Promise.all([loadTopicsSummary(), loadNoteData()])`) *and* a separate
  `$effect(() => topicId && loadNoteData())`. Combined with the in-flight GET
  dedupe in `api.ts`, this produced overlapping loads that each reset
  `loading=true`/`noteDetails=null`, with no guard ensuring the *latest* load
  owns the final `loading=false`. On direct load/refresh the two triggers raced
  and could strand the spinner ("Opening study folder…").
- **Scroll corruption:** There is **no scroll JS** in the notes feature (no
  `IntersectionObserver`, scroll handlers, or session/localStorage). So scrolling
  cannot itself change state — the "content replaced by loading skeleton" was the
  same load race re-firing/stranding `loading`, plus the unstable nested-scroll
  layout (a `sticky` TOC card promoted into its own paint layer). Fixed at the
  source with a single load trigger + stale-response guard, and by removing the
  sticky.
- **Markdown rendering:** `NoteSection.svelte` used a hand-rolled parser that only
  handled `**bold**`, `` `code` ``, and `- ` bullets — **no `###` headings, no
  `*`/`+` bullets, no GFM `|` tables**. Those rendered as raw text. It was the
  only render path, so unifying it fixes every section consistently.
- **Layout/sidebar issues:** The right column is a fixed-height `overflow-y-auto`
  scroller; the `TocPanel` had `sticky top-20`, which made it overlap the
  checklist and start mid-scroll.

## Files changed
- `frontend/src/lib/markdown.ts` — **new** shared, XSS-safe Markdown→HTML renderer.
- `frontend/src/lib/components/notes/NoteSection.svelte` — use shared renderer; fix Mark Read checkbox alignment.
- `frontend/src/lib/components/notes/TocPanel.svelte` — removed `sticky top-20` (overlap/mid-scroll).
- `frontend/src/routes/topics/[topicId]/notes/+page.svelte` — single reactive load + stale-response guard; admin-gated compact draft banner; `<h1>` topic title; segmented tabs; right-sidebar scroll-to-top on topic change.
- `frontend/src/routes/+layout.svelte` — zero-streak text.
- `frontend/e2e/markdown-render.spec.ts` — **new** renderer regression spec.

## Critical fixes

**1. Direct URL infinite loading**
- Root cause: dual load triggers (`onMount` + `$effect`) racing through the `api.ts` GET dedupe, no "latest load wins" guard.
- Fix: removed the `onMount` note-load; notes now load from a **single** `$effect` keyed on `topicId` (fires identically for direct URL, refresh, back/forward, in-app switch). Added a monotonic `loadSeq` so only the most recent request commits its result and toggles `loading`. Topics list + roles load independently and never block the notes.
- Retest: `pnpm check` 0/0; `pnpm build` ✓; logic verified — `loading` is always resolved by the latest load.

**2. Scroll-triggered state corruption**
- Root cause: not scroll code (there is none) — the same load race plus a `sticky` TOC layer over a nested scroller.
- Fix: stale-response guard (above) means no late response can blank the content; removed the `sticky` TOC; right column is a single clean scroller.
- Retest: build ✓; with the guard, a superseded load returns early instead of resetting `noteDetails`/`loading`.

## High fixes

**3 & 4. Markdown + table rendering (unified)**
- Root cause: limited bespoke parser, no headings/tables/`*` bullets; single path so all sections were affected equally.
- Fix: one shared `renderMarkdown()` — headings, ordered/unordered lists, bold/italic, inline + fenced code, **GFM pipe tables**, blockquotes, links. **Escape-first** safety: source is HTML-escaped before any markup is injected, so `{@html}` output cannot carry script/attribute injection; links restricted to http/https/mailto with `rel="noopener noreferrer nofollow"`.
- Retest: 13/13 renderer assertions pass (headings, `*`/`-` bullets, GFM tables, fenced code, italic, safe + neutralized links, and XSS: no raw `<img>`/`<script>`, `<` escaped).

## Medium fixes

- **5. Header tabs/bookmark:** view toggles are now an explicit `role="tablist"` segmented control with `aria-selected`; inactive tabs get a hover background so they read as clickable; bookmark is a separate pill (amber when active, `aria-pressed`) with a divider before the tabs.
- **6. Heading hierarchy:** the topic name is now the page `<h1>` (was `<h2>`); removed the competing inline duplication.
- **7. Admin draft banner:** removed from the note body; replaced with a **compact, admin-only** notice (`isAdmin && is_preview`, role from `/auth/me`) at the top of the content column with a quiet "Review queue" link. Non-admins never see it.
- **8. Scroll architecture / right sidebar:** removed the sticky TOC (overlap fixed in a prior step), and the right column now resets to the top on topic change via a `bind:this` ref + effect, so it starts at "Table of Contents". Kept the app-shell columns (converting the whole app to a single page scroll would be a global-layout refactor beyond this page — see Remaining).
- **9. Mark Read checkbox:** aligned (`w-4 h-4 shrink-0`, `accent-blue-600`, focus ring), label `leading-none`; keyboard-accessible (native checkbox + label).
- **10. Zero streak:** shows "Start your streak today" instead of "0 Day Streak".

## Tests added/updated
- `frontend/e2e/markdown-render.spec.ts` — 6 specs covering headings, lists+bold, GFM tables, fenced code/italic, XSS escaping, and link scheme safety.

## Commands run
| Command | Result |
|---|---|
| `pnpm check` (svelte-check) | 0 errors / 0 warnings (825 files) |
| `pnpm build` (vite SSR+client) | ✓ built (pre-existing adapter-auto note only) |
| Node TS-strip renderer assertions | **13/13 passed** |

## Browser verification
- Direct URL / Refresh / Back-forward: load path is now a single `topicId`-keyed effect that runs on mount in every case; SSR compiles (build ✓). **Full live click-through against the running stack (backend :8000 + seeded topic 2) was not executed in this environment** — see Remaining.
- Scroll bottom: no scroll JS + stale-guard ⇒ content cannot be blanked by a late load.
- Markdown / Tables: verified via the 13 renderer assertions.
- Console / Network: no new client errors in type-check/build; `/auth/me` is the one added request (already an existing, tested endpoint).

## Remaining issues
- **Live end-to-end browser run** (direct load on `/topics/2/notes`, scroll, admin vs non-admin banner) needs the backend + a seeded topic and a logged-in token; recommended next step: run `pnpm test:e2e` with uvicorn on :8000 and a `pw-e2e-*@test.dev` user, and add a page-level spec that injects a token and asserts the notes render (not the spinner).
- **Single-page-scroll refactor (issue #8 stretch):** the page keeps the fixed-height app-shell with inner scrollers (now stable). Collapsing to one page scroll touches the global `+layout` height model for all routes and was intentionally left out to avoid an unrelated large refactor.

## Final status
**Working** — critical load race and markdown/table rendering fixed and verified by type-check, build, and 13 renderer assertions; all medium UI/UX items addressed. The only un-run item is the live multi-service browser click-through, which requires the running backend + seeded data (steps documented above).
