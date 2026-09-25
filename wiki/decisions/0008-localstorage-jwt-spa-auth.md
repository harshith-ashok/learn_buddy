# 0008: localStorage JWTs and client-rendered auth, not cookies + Proxy

## Problem

The frontend needs to attach the Phase 4 API's bearer token to every
request and gate pages behind a session. Next.js (App Router) offers two
broadly different shapes for this: cookie-based tokens read server-side
(in Server Components / Proxy — Next 16's renamed Middleware, see
`node_modules/next/dist/docs/01-app/01-getting-started/16-proxy.md`), or
tokens held client-side and checked in the browser.

## Options considered

- **Cookies + Proxy.** The access/refresh tokens would live in
  `httpOnly` cookies, verified in `proxy.ts` before a protected route
  even renders, and Server Components could fetch with the cookie
  attached. More resistant to XSS token theft. But it means either the
  Next server proxies every API call (extra hop, and `core/llm_client.py`
  webrequests would then log through two services), or Server Components
  call `NEXT_PUBLIC_API_URL` directly with a forwarded cookie — workable,
  but a materially bigger surface for a Phase 5 scope that's really one
  API, one frontend, both already CORS-enabled.
- **localStorage + client components.** `lib/token-store.ts` owns
  read/write; `lib/api.ts` attaches the header and silently refreshes on
  a 401. Every data-bearing page is a Client Component (`AuthGuard`
  wrapping a React Query-driven view) — simpler to reason about with one
  API origin, at the cost of tokens being readable by any script on the
  page (XSS exposure) and no server-rendered authenticated content.

## Choice

localStorage + client components. This is a small, single-origin app
with no server-rendered personalized content to protect, and standing up
Proxy-based cookie auth would be solving a problem this phase doesn't
have yet. `core/config.py: cors_allowed_origins` is what makes the
client-side calls to a separate API origin work at all — see the CORS
follow-up in `phases/phase-5-frontend.md`.

## Consequences

- No XSS hardening story beyond "don't introduce an XSS bug" — there's
  no CSP or trusted-types work in this phase. Revisit if the app ever
  needs to render arbitrary/third-party content.
- Every protected page pays a client-side round trip before showing
  content (`AuthGuard`'s brief "Checking your session…" state) — there's
  no server-rendered fast path for an authenticated first paint.
- Revisiting this later (e.g. for SSR'd authenticated pages) means a real
  migration, not a config flip — cookies + Proxy is a different shape,
  not an incremental extension of this one.
