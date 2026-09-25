# Phase 1 — Backend Foundations & Data Model

**Goal** (from `TODO.md`): lay down the `backend/src/` package structure
from `CLAUDE.md`, the 8 SQLAlchemy models and their initial Alembic
migration, async Postgres/Redis/Chroma clients, JWT auth, the `{code,
message}` error envelope, structured logging, and a pytest scaffold with a
real (dockerized) Postgres fixture.

## What was built

- **Package layout** under `backend/src/`: `api/`, `domain/` (empty —
  nothing to hold yet), `agents/` (empty), `ingestion/` (empty), `db/`,
  `core/`, matching `CLAUDE.md` exactly. `backend/main.py` was removed;
  the app now lives at `src/main.py` (`create_app()`), served as
  `uvicorn src.main:app` (Dockerfile and override both updated).
- **8 SQLAlchemy models** (`db/models/`) — `students`, `documents`,
  `topics`, `subtopics`, `topic_prerequisites`, `mastery_scores`,
  `study_kits`, `quiz_attempts` — UUID PKs and timestamps via shared
  mixins, a fixed constraint-naming convention (`db/base.py`). Full shape
  in [data-model.md](../data-model.md).
- **Alembic** (`backend/migrations/`, `backend/alembic.ini`), async
  (`run_sync` pattern), reading `DATABASE_URL` from the same `Settings`
  object the app uses. One migration (`initial schema`) creates all 8
  tables; verified `upgrade head` → `downgrade base` → `upgrade head`
  round-trips cleanly (needed a manual fix for Alembic not auto-dropping
  Postgres `ENUM` types on downgrade — see `runbook.md`).
- **`core/config.py`** — `pydantic-settings` `Settings`, defaults chosen to
  match `.env.example` so tests/tools work against the dockerized services
  with zero config out of the box.
- **`core/cache.py`** — Redis wrapper (`redis.asyncio`) with session-key
  and rate-limit-key helpers, plus an atomic `incr_with_ttl` for
  fixed-window rate limiting.
- **`core/vectorstore.py`** — thin wrapper around `chromadb.HttpClient`,
  one-collection-per-student naming.
- **`core/security.py`** — bcrypt password hashing; HS256 JWT access
  (15 min default) and refresh (7 day default) tokens, typed
  (`TokenType.ACCESS`/`REFRESH`) so a refresh token can't be used where an
  access token is expected.
- **`api/deps.py`** — `get_current_student` FastAPI dependency (bearer
  token → `Student` row); every protected route will depend on this
  rather than trusting a client-supplied id.
- **`core/errors.py`** — `AppError` and subclasses
  (`NotFoundError`/`UnauthorizedError`/`ForbiddenError`/`ConflictError`),
  plus handlers registered in `create_app()` so `AppError`, FastAPI
  validation errors, `HTTPException`, and any unhandled exception all come
  back as `{code, message}` JSON.
- **`core/logging.py`** — one-time JSON logging setup
  (`python-json-logger`) to stdout, wired into uvicorn's loggers too.
- **pytest scaffold** — `tests/conftest.py` spins up a dedicated
  `<db>_test` Postgres database per session, applies
  `Base.metadata.create_all` once, and gives each test an isolated
  transaction+savepoint session so `commit()` in code under test doesn't
  leak between tests. 13 tests across `core/` (security, errors, cache)
  and `db/` (model roundtrip + constraint enforcement) and `api/` (health
  through the full FastAPI+DB dependency chain).
- `ruff` config (`[tool.ruff]`) added to `pyproject.toml`; `ruff format` +
  `ruff check --fix` run clean across the new code.

## What a new engineer needs to know

- Two `.env` files exist on purpose: the root one is what `docker-compose`
  feeds the containers (service DNS names — `postgres`, `redis`,
  `chromadb`); `backend/.env` (gitignored, `backend/.env.example` checked
  in) is what `alembic`/`pytest` read when run directly on the host
  (`localhost` + published ports). See `runbook.md`.
- This dev machine had a pre-existing Postgres bound to `127.0.0.1:5432`
  outside Docker, which silently shadowed the container's published port.
  Fixed locally by moving `POSTGRES_PORT` to `5433`; if you don't hit this,
  the default `5432` is fine. `runbook.md` has the diagnostic.
- pytest-asyncio needs **both** `asyncio_default_fixture_loop_scope` and
  `asyncio_default_test_loop_scope` set to `"session"` for a session-scoped
  async engine fixture to work — setting only the fixture one still breaks
  with a cross-event-loop error.
- Alembic autogenerate does not emit `DROP TYPE` for Postgres enums on
  table drop; every downgrade touching an enum column needs that added by
  hand (already done for `document_status`/`study_kit_type` in the initial
  migration).
- `chromadb-client` is pinned to `0.5.20` to match the `chromadb/chroma`
  server image tag from Phase 0 — the full `chromadb` package (not
  `-client`) pulls in `onnxruntime`, which has no Python 3.10 wheel, and
  a newer client major version risks wire-protocol incompatibility with
  the pinned 0.5.x server. See
  [decisions/0002-thin-chroma-client.md](../decisions/0002-thin-chroma-client.md).

## Verification

`uv run pytest` — 13 passed. `alembic upgrade head` → `downgrade base` →
`upgrade head` round-trip clean, `alembic check` reports no drift between
models and the migration. Rebuilt the Docker images
(`docker compose up -d --build`): all five services healthy again,
`GET /health` → `200`, and `alembic current` run inside the running
`backend` container confirms it sees the same schema at the same
revision as the host-run migration (same underlying Postgres, reached via
two different routes).

## Deviations from the plan

- Added `ruff` as a dev dependency (Phase 0, noted there) and a
  `[tool.ruff]` config now that there's real code to lint.
- `TODO.md` doesn't list a `courses` table, but Phase 3's "exam-date
  weighting" needs an exam date somewhere; put `exam_date` (nullable) on
  `documents` rather than inventing a new table, since one document is
  already the closest thing to "a course" in the current schema.
- Chose `chromadb-client==0.5.20` over the full `chromadb` package — not
  specified either way in `TODO.md`; see the ADR linked above.
