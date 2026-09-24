# frontend

Next.js (App Router) UI, `npm`-managed. See the repo root
[README.md](../README.md) for the full local-setup instructions — this
needs the `backend` API reachable (`NEXT_PUBLIC_API_URL`) to do anything
useful; it isn't a standalone app.

```bash
cp .env.example .env.local   # NEXT_PUBLIC_API_URL — see the file for defaults
npm install
npm run dev
```

```bash
npm run lint          # eslint
npm run type-check    # tsc --noEmit
npm run build          # production build (also type-checks)
```

Layout and conventions: [../wiki/architecture.md](../wiki/architecture.md)
→ "Frontend internals". Every route/component: [../wiki/phases/phase-5-frontend.md](../wiki/phases/phase-5-frontend.md).
