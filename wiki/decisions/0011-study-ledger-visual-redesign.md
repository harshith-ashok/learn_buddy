# ADR 0011: Redesign the frontend around a single dark "Study Ledger" theme

## Problem

Phase 5 shipped a working but visually generic UI: an indigo `brand-*`
palette, light/dark via `prefers-color-scheme`, and Geist fonts — a
default Tailwind-starter look, not a considered design. The user
supplied a static HTML/CSS/JS mockup (`ref.html`, a "Study Ledger" —
dark, editorial, Work Sans + IBM Plex Mono, mustard/moss/rust accents,
ledger-row topic list, a mastery dial, prerequisite chain diagram) and
asked for the real app to be redesigned around it.

## Options considered

1. Keep the token *names* and *light/dark* structure, just swap the hex
   values to approximate the mockup's palette.
2. Replace `styles/theme.css` outright with a single always-dark palette
   matching `ref.html`, keep the existing token *names*
   (`--color-brand-*`, `--color-surface*`, ...) so every component
   class (`bg-brand-500`, `text-ink-muted`, ...) keeps working, and
   rebuild each page's markup/layout to match the mockup's composition
   rather than just recoloring the old layout.

## Choice

Option 2. `ref.html` is a single deliberately-dark editorial theme
(`color-scheme: dark` in its own `:root`, no light variant) — approximating
it under a light/dark toggle would produce a design nobody asked for and
never designed a light mode for. Token *names* were kept unchanged
(`--color-brand-500` is now a mustard, not an indigo) so this was a
content-only diff to `theme.css` plus `globals.css`'s font vars, not a
rename across every component.

Layout changes beyond recoloring, to match `ref.html`'s composition
rather than just its palette:

- `NavBar` → `components/masthead.tsx`: a large wordmark + kicker +
  underline nav, replacing the old thin top bar. Added a real "days to
  exam" badge (`lib/hooks/use-exam-countdown.ts`, derived from the
  nearest upcoming `document.exam_date` across the student's documents —
  no such aggregate existed before).
- `dashboard/page.tsx`'s `RecommendationCard` + `MasteryList` →
  `components/dashboard/`: a two-column rail-and-ledger layout
  (`recommended-next`, `remediation-alert`, `unit-filters`,
  `topic-ledger`), filterable by document. `unit-filters` groups by
  `document_id` since the API has no separate "unit" concept — a
  document *is* the closest existing grouping (see `api-reference.md`'s
  `course_id === document_id` note).
- `study-kit-page-content.tsx` → `components/topic/`: the study-kit tabs
  now sit under a real topic header (`useCourseGraph` for description /
  subtopics / prerequisite edges, previously unused on this page) with a
  mastery ring (`ui/mastery-dial.tsx`) and prerequisite/unlocks chains
  (`topic/prerequisite-chain.tsx`), not just a bare tab strip.
- `ui/progress-bar.tsx` → `ui/mastery-ticks.tsx`: a 20-segment tick
  meter (rust/mustard/moss by score band) replacing the single filled
  bar, used in the ledger; `mastery-dial.tsx` reuses the same color
  function for the topic-page ring.

No fabricated data: `ref.html`'s static mock included a per-concept
mastery breakdown and a "recent attempts" sparkline that the API has no
backing data for (only topic-level `mastery_score`, no historical quiz
log or per-subtopic score). Those two elements were dropped rather than
faked — subtopics render as a plain list, no invented percentages or
history chart.

## Consequences

- No light mode exists. If one is wanted later, `theme.css` needs a
  second palette and every component needs to be checked against it —
  this redesign did not preserve the old light-mode values anywhere.
- `frontend/src/components/nav-bar.tsx`, `recommendation-card.tsx`,
  `mastery-list.tsx`, `ui/progress-bar.tsx`, and
  `study-kit/study-kit-page-content.tsx` were deleted outright (not kept
  as dead code) — their replacements are listed above.
- Verified against the real stack, not just `next build`: a Playwright
  script drove register → upload → dashboard → topic page → generate
  summary/flashcards/quiz through the actual dev server and `backend`
  container (real LLM-generated content, not fixtures), at both a
  1440px and a 390px viewport, with `console --errors` checked clean.
