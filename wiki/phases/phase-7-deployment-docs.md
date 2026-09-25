# Phase 7 — Deployment & Docs

## Goal

A production-shaped `docker compose` deployment (no dev bind-mounts,
resource limits, log rotation) that's actually been brought up and
exercised, not just written — and a final pass making sure
`architecture.md`, `runbook.md`, and `api-reference.md` describe the
system as it actually ships, plus the root `README.md` reads as a real
getting-started path.

## What was built

- **`docker-compose.prod.yml`** — a `-f`-explicit overlay (never
  auto-merged, unlike the dev override): `restart: always`, per-service
  CPU/memory `deploy.resources` limits and reservations, and log
  rotation. Brought up for real (`docker compose -f docker-compose.yml -f
  docker-compose.prod.yml up -d --build`), migrated, and health-checked
  before being trusted — see "Harder than expected".
- **`docker-compose.yml` (base) hardened**: `postgres`/`redis`/`chromadb`
  no longer publish a host port at all — moved to
  `docker-compose.override.yml` (dev-only, auto-applied for every normal
  `docker compose up`) instead, so nothing about the everyday dev
  workflow changed, but a bare `docker-compose.yml` (what the prod
  overlay builds on) no longer exposes the datastores beyond
  `learn_buddy_net`.
- **`decisions/0009`**: `target: runtime` pinned explicitly on `backend`
  and `frontend` — see "Harder than expected" for why this was a real,
  previously-invisible bug, not preventative hardening.
- **Wiki pass**: `architecture.md`'s "Local vs. production compose"
  section rewritten for the two overlays' actual (different) merge
  behavior; `runbook.md` gained a "Production deployment" section (the
  env vars that matter before the first prod `up`, and why
  `NEXT_PUBLIC_API_URL` specifically has to be right *before* `--build`,
  not after). `api-reference.md` checked against the live OpenAPI spec —
  already accurate, no changes needed.
- **Root `README.md`**: reviewed end-to-end as a new developer would
  read it — see "Deviations" for what changed.

## Harder than expected

`docker compose up -d --build` had "worked" for the backend on every run
across Phases 4–6 — and was silently building the wrong image the whole
time. `backend/Dockerfile` gained a `test` stage in Phase 4, appended
*after* `runtime`; Docker builds the last stage in a file when nothing
says otherwise, and `docker-compose.yml` never pinned one. Every local
`docker compose up` auto-merges `docker-compose.override.yml`, which
sets an explicit `command:` — masking that the underlying *image* was
`test` (`CMD ["uv", "run", "pytest", ...]`), not `runtime`, the entire
time. A deployment running the base `docker-compose.yml` alone — exactly
what this phase's production overlay is the first thing to ever do —
would have built a container that runs the test suite once and exits,
never serving traffic.

Caught by hand, not by review: `docker inspect learn_buddy-backend
--format '{{.Config.Cmd}}'` after a bare `docker compose -f
docker-compose.yml build backend`, before trusting the prod overlay to
build on top of it. Fixing it surfaced a second, related gap in the same
motion — the `runtime` stage never had `uv` on `PATH` (only
`builder`/`test` do), so every documented "run migrations inside the
container" instruction (`docker compose exec backend uv run alembic
upgrade head`, in `Makefile`, `wiki/runbook.md`, and
`.github/workflows/ci.yml`) had also only ever worked by the same
accident. Fixed by dropping the `uv run` prefix — `alembic` is a real,
non-dev dependency, already on the `runtime` venv's own `PATH`. Full
account in [decisions/0009](../decisions/0009-pin-docker-build-target.md).

Once that was fixed, removing the datastores' published ports (the
originally-planned piece of this phase) hit a second surprise: Compose
doesn't let an overlay *remove* something the base file publishes —
list-valued fields like `ports` concatenate across merged compose files,
they don't replace, so `docker-compose.prod.yml` setting `ports: []` was
a silent no-op (verified with `docker compose config`, not assumed). Fixed
by inverting the ownership instead: the base file publishes nothing for
the datastores, and `docker-compose.override.yml` (already dev-only, already
auto-applied for every plain `docker compose up`) adds the host ports
back — so normal dev workflows are provably unchanged (checked via `docker
compose config` before and after), while a bare base-file or prod-overlay
build now correctly keeps the datastores off the host entirely.

## Deviations from the plan

- `TODO.md` only asks for `docker-compose.prod.yml`, not for fixing the
  base `docker-compose.yml` — but the build-target bug lived in the base
  file, and the "no published datastore ports" hardening turned out to
  belong there too (an overlay structurally can't remove it) — see
  "Harder than expected".
- Went with the `docker-compose.prod.yml` option `TODO.md` offers (vs.
  Fargate/EKS manifests) — this project has no existing cloud deployment
  target to write manifests against, and the compose-based path is what
  the whole project has run on through every prior phase.
