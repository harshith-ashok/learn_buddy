# 0009: Pin `target: runtime` explicitly for backend and frontend

## Problem

Docker builds the *last* stage in a Dockerfile when nothing says
otherwise. `backend/Dockerfile` was `builder` → `runtime` → `test` (the
`test` stage added in Phase 4, appended after `runtime`) — so any build
without an explicit `--target`/`target:` silently built `test`, not
`runtime`. `docker-compose.yml`'s `backend` service never set one.

This was invisible for three phases. Every local `docker compose up`
implicitly merges `docker-compose.override.yml`, which sets `command:
["uvicorn", ...]` explicitly — masking the fact that the *image* being
run was the `test` stage (`CMD ["uv", "run", "pytest", ...]`), not
`runtime`. `docker compose up -d --build` "worked" every time in this
project's whole history so far, for the wrong reason. A deployment using
`docker-compose.yml` on its own (no override — the base file being the
whole point of a "production compose" per `TODO.md` Phase 7) would have
built and run a container whose actual command is `uv run pytest`, not
`uvicorn` — never serving traffic. Found only because Phase 7's
production overlay is the first thing to ever build and run
`docker-compose.yml` without the override.

## Options considered

- **Reorder the Dockerfile so `runtime` is last.** Works today, but the
  bug returns the next time a stage is appended after it (e.g. `test`
  was itself appended after `runtime` once already) — a footgun that
  depends on remembering an ordering invariant forever.
- **Pin `target: runtime` explicitly on the `backend` and `frontend`
  services in `docker-compose.yml`.** Makes the default build target a
  property of the compose file (reviewed, versioned, obviously wrong if
  someone changes it to `test` by mistake), not an emergent property of
  Dockerfile stage order.

## Choice

Pin `target: runtime` on both services in the base `docker-compose.yml`.
`frontend/Dockerfile` didn't have this bug (`runtime` was already its
last stage), but got the same explicit pin anyway — free insurance
against the identical mistake if a stage is ever appended after it.

## Consequences

- `docker-compose.yml` alone (no override, no prod overlay) now builds
  and runs the correct image — verified by hand: `docker compose -f
  docker-compose.yml build backend frontend` then `docker inspect
  learn_buddy-backend --format '{{.Config.Cmd}}'` shows the `uvicorn`
  command, not `pytest`.
- Surfaced a second, related gap: the `runtime` stage never had `uv` on
  PATH (only `builder`/`test` do) — every "run migrations inside the
  container" instruction that used `uv run alembic upgrade head` had
  only ever worked because the container was accidentally running the
  `test`-stage image. Fixed by dropping the `uv run` prefix — `alembic`
  is a real (non-dev) dependency, already on the `runtime` venv's PATH —
  everywhere that instruction appeared: `Makefile`'s `migrate` target,
  `wiki/runbook.md`, and `.github/workflows/ci.yml`'s
  `compose-integration` job.
