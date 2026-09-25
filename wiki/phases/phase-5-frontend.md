# Phase 5 — Frontend

## Goal

A working Next.js UI over the Phase 4 API: register/login, drag-and-drop
upload with visible ingestion progress, a mastery dashboard with a
next-topic recommendation card, and four study-kit views (summary,
flashcards with a flip interaction, a gradable quiz, a problem guide) —
all through one typed API client, React Query for data fetching, and a
centralized set of Tailwind design tokens instead of one-off values
scattered through components.

## What was built

- **`frontend/src/`** — moved `app/` under `src/app/` (it was at the
  repo root since Phase 0's scaffold, a drift from `CLAUDE.md`'s file
  structure never caught until this phase actually populated it) and
  added `components/`, `lib/`, `styles/` alongside it. `tsconfig.json`'s
  `@/*` path now resolves to `./src/*`.
- **`styles/theme.css`** — every color, radius used anywhere in the app
  as a `@theme` token (`--color-brand-*`, `--color-surface*`,
  `--color-ink*`, status colors, `--radius-card`/`--radius-control`),
  light/dark via `@media (prefers-color-scheme: dark)`. Components use
  the generated utilities (`bg-brand-600`, `text-ink-muted`,
  `rounded-card`, ...) — no raw hex or one-off arbitrary values in a
  component file. `TODO.md` says `tailwind.config.ts`; Tailwind 4 (already
  the project's version) has no such file — tokens are CSS-native via
  `@theme`, which is that version's actual mechanism for the same intent.
- **`lib/token-store.ts`**, **`lib/api.ts`** — the one typed client.
  Tokens live in `localStorage` (see
  [decisions/0008](../decisions/0008-localstorage-jwt-spa-auth.md));
  `api.ts` attaches the bearer header, retries once through a
  de-duplicated silent refresh on a 401, and every endpoint (auth,
  documents, graph, progress, recommendation, study-kit, quiz) has a
  typed function. `lib/types.ts` mirrors every backend Pydantic schema.
- **`lib/auth-context.tsx`** + **`lib/providers.tsx`** — `AuthProvider`
  (login/register/logout, decodes the access token's `sub` client-side)
  and a `QueryClientProvider` per the TanStack Query guide bundled in
  `node_modules/next/dist/docs` for this Next version.
- **`lib/hooks/`** — one React Query hook module per domain
  (`use-documents`, `use-course-graph`, `use-progress`,
  `use-recommendation`, `use-study-kit`, `use-quiz`), each gated on
  `isAuthenticated && !isLoading`. `useDocuments` polls every 2s while
  any document is still `pending`/`processing` — that's the "ingestion
  progress" `TODO.md` asks for; the API has no finer-grained percentage
  to show.
- **Pages**: `/`, `/login`, `/register`, `/upload` (drag-and-drop +
  document status list), `/dashboard` (recommendation card + mastery
  list), `/study-kit/[topicId]` (tabbed summary/flashcards/quiz/problem-
  guide, generate-or-regenerate per tab).
- **`components/study-kit/`** — one view component per kit type;
  `flashcards-view.tsx` does the flip with a CSS 3D transform
  (`[transform-style:preserve-3d]` + `rotateY`), no animation library.
  `quiz-view.tsx` grades via `POST /quiz/submit` and renders the
  remediation plan inline when one comes back.
- **Verified against the real stack**, not just `npm run build`: a
  Playwright script (ad hoc, not checked in — no frontend test framework
  exists yet, out of this phase's scope) drove register → dashboard →
  upload → logout → redirect-to-login through the actual dev server and
  the actual `backend` container, then a second pass seeded real
  `study_kits` rows directly in Postgres and drove all four kit tabs,
  the flashcard flip, and a quiz submission end to end. Caught two real
  bugs — see "Harder than expected".

## Harder than expected

**No CORS on the backend.** The very first real browser request (not
`curl`, not `ASGITransport`) failed: `Access to fetch ... has been
blocked by CORS policy`. Every backend test to this point talked to the
app in-process or from a non-browser HTTP client, so nothing had ever
exercised a real cross-origin preflight. Fixed in `backend/src/main.py`
(`CORSMiddleware`, origins from the new `CORS_ALLOWED_ORIGINS` env var)
— a backend change, but one this phase's own verification is what
surfaced, so it landed here rather than waiting for a Phase 4 revisit.
Regression-tested in `backend/tests/api/test_cors.py`.

**A `useSyncExternalStore`-based auth read looked more "correct" and
wasn't.** The textbook-clean way to read a client-only store
(`localStorage`, via `token-store.ts`) without an effect-driven
`setState` is `useSyncExternalStore`, and it's what `auth-context.tsx`
used first. It compiled, typechecked, and passed lint — and then failed
in the actual browser: reloading an authenticated page briefly
redirected to `/login` anyway, because a sibling component's redirect
effect ran against the still-server-matched (unauthenticated) snapshot
before the hook's client resync had definitely landed. Reverted to an
explicit `useEffect` + `isLoading` flag (the "old" pattern), which is
what `eslint-plugin-react-hooks`'s `set-state-in-effect` rule flags —
suppressed with a one-line comment explaining why, since the alternative
it wants demonstrably broke in practice. Only caught by actually driving
a browser against a live reload, not by any static check.

## Deviations from the plan

- `TODO.md`'s Phase 5 list has no auth pages — same gap as Phase 4's
  missing `/auth/*` router (see `phases/phase-4-api-layer.md`). Added
  `/login` and `/register`, sharing one `AuthForm` component.
- `GET /study-kit?topic_id=` / `GET /study-kit/{id}` (added while
  building this phase, see `phases/phase-4-api-layer.md`'s follow-up)
  are what `study-kit-page-content.tsx` uses to redisplay a previously
  generated kit — without them, refreshing the page would lose it.
