# Phase 0 — Docker Foundation & Project Skeleton

**Goal** (from `TODO.md`): stand up `docker-compose.yml` with five
independent, healthy services (`backend`, `frontend`, `postgres`, `redis`,
`chromadb`), each with its own Dockerfile, wired to `.env` config, with no
real application code yet beyond a backend `/health` check and the
default Next.js page.

## What was built

- **`docker-compose.yml`** — five services on a `learn_buddy_net` bridge
  network, named volumes for `postgres`/`redis`/`chromadb` data,
  `depends_on: condition: service_healthy` chaining
  (`backend` → postgres/redis/chromadb; `frontend` → backend), all
  configuration pulled from `.env` via `env_file` + compose variable
  substitution.
- **`docker-compose.override.yml`** — dev-only overlay, applied
  automatically. Bind-mounts source into `backend` and `frontend`, runs
  `uvicorn --reload` and the frontend's `dev` build stage (`next dev`).
  Container-only dirs (`.venv`, `node_modules`, `.next`) are pinned to
  anonymous volumes so the source bind mount doesn't shadow them.
- **`backend/Dockerfile`** — two-stage `uv` build: builder stage does
  `uv sync --frozen` against the committed `uv.lock`, runtime stage
  (`python:3.10-slim`) copies only `/app` (venv + source) and runs as a
  non-root `app` user. `backend/main.py` now exposes a real
  `FastAPI` app with `GET /health`.
- **`frontend/Dockerfile`** — `deps` → `builder` → `runtime` stages, plus a
  fourth `dev` stage the override targets. `next.config.ts` now sets
  `output: "standalone"` so the runtime stage only needs
  `.next/standalone` + `.next/static` + `public`, not `node_modules`.
- **`postgres`** (`postgres:16-alpine`), **`redis`** (`redis:7-alpine`,
  `--appendonly yes`), **`chromadb`** (`chromadb/chroma:0.5.20`) — each
  pinned, each with a healthcheck compose actually waits on.
- **`.env.example`** at the repo root documenting every variable the
  compose file and (future) backend config will read; `.env` is gitignored.
- **`Makefile`** with `up`, `down`, `logs`, `ps`, `build`, `test`,
  `migrate`, `lint`, `fmt`, `clean`.
- **Root `README.md`** — architecture table, one-command setup
  (`cp .env.example .env && make up`), pointers into `wiki/`.
- **`.dockerignore`** for both services; root **`.gitignore`** extended
  with `.env`, Python and Node build/cache artifacts.

## What a new engineer needs to know

- `docker compose up` (or `make up`) with no args gets the dev overlay for
  free — that's live-reload, not the production image. To build/run the
  exact images that would ship, use `docker compose -f docker-compose.yml
  up` (no override) or `docker build --target runtime ./frontend` /
  `docker build ./backend` directly.
- Chroma's container port is always `8000` internally; its host port is
  `CHROMA_PORT` (default `8001`) specifically to avoid colliding with the
  backend's host port `8000`.
- The backend Dockerfile pins `python:3.10-slim` to match
  `backend/.python-version` (`3.10`) and `uv.lock`'s resolved
  `requires-python` — using a newer base image risked a lockfile/interpreter
  mismatch inside the container that wouldn't show up locally.
- `ruff` was added as a backend dev dependency in this phase (not listed in
  the Phase 0 checklist, but `make lint` and `CLAUDE.md`'s formatting
  standard both needed it to mean something) — see
  [decisions/0001-ruff-as-dev-dependency.md](../decisions/0001-ruff-as-dev-dependency.md).
- No knowledge-graph/agent code exists yet; `backend/main.py` is
  intentionally just a health check until Phase 1 lays down the real
  `src/` package structure from `CLAUDE.md`.

## Verification

Ran `docker compose up --build -d` from a clean state: all five containers
reported `healthy` (`frontend`'s dev-stage container has no healthcheck
defined, matching the runtime-stage-only `HEALTHCHECK` in the Dockerfile;
it was confirmed serving `200` manually instead).
`curl http://localhost:8000/health` → `{"status":"ok"}`.
`curl http://localhost:3000` → `200` (default Next.js page). Also built and
ran the `runtime` target directly (bypassing the dev override) to confirm
the production standalone image serves `200` on its own.

## Deviations from the plan

None — matches the Phase 0 checklist in `TODO.md`, plus the ruff addition
noted above.
