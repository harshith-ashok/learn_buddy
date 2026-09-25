# ADR 0013: Sidebar + top bar app shell, replacing the hero masthead

## Problem

[decisions/0011](0011-study-ledger-visual-redesign.md) replaced the
original thin nav bar with a large hero-style masthead: a big "Study
Ledger" wordmark, inline nav links underneath it, and an exam-countdown
badge, repeated at the top of every authenticated page. Asked directly
for "a traditional sidebar and top bar design" instead — the masthead's
editorial framing was costing real vertical space and page-to-page
consistency (the title/nav block re-rendered and re-animated on every
navigation) for a workflow app used repeatedly, not a one-time landing
moment.

## Choice

Replaced `components/masthead.tsx` with three components:

- `sidebar.tsx` — persistent left nav (`md:` and up), wordmark at top,
  the two nav links with left-accent active state, `sticky top-0
  h-screen` so it doesn't scroll with page content.
- `topbar.tsx` — slim (`h-16`) horizontal bar to the right of the
  sidebar: current page label on the left, exam countdown + sign-out on
  the right. `sticky top-0 z-10` — pinned above scrolling page content.
- `app-shell.tsx` — the auth-gated switch: renders sidebar+topbar around
  `children` when authenticated, or just `children` otherwise (unchanged
  behavior from the old masthead's own `if (!isAuthenticated) return
  null`). Lives in `layout.tsx` in place of `<Masthead />`.

Below `md`, the sidebar hides entirely and the top bar absorbs the
wordmark and nav links inline (`topbar.tsx`'s `MOBILE_LINKS`) — a
persistent fixed sidebar doesn't fit a phone-width viewport, but losing
navigation entirely below `md` wasn't acceptable either.

## Consequences

- `dashboard-content.tsx`'s rail (`RecommendedNext` + filters) sticks
  under the fixed top bar now, not the top of the viewport — its sticky
  offset moved from `md:top-6` to `md:top-22` (88px = the 64px top bar
  plus the original 24px gap) so it doesn't slide under the bar while
  scrolling.
- The dot-grid decorative background and the large italic wordmark
  treatment from the masthead stay only on the logged-out landing page
  (`app/page.tsx`) and `auth-form.tsx` — intentional: a one-time
  marketing/auth moment can still afford that treatment; the app shell a
  logged-in student sees on every page load should not.
- No page-level content padding changed (`dashboard-content.tsx`,
  `topic-page-content.tsx`, `upload/page.tsx` keep their own `mx-auto
  max-w-*` containers) — they now sit in the remaining width next to a
  256px (`w-64`) sidebar instead of full viewport width, which at the
  app's actual content widths (max 1180px) made no visible difference.
