# Runbook

How to run this locally, and fixes for the failures you'll actually hit.

## Full stack (Docker)

```bash
cp .env.example .env
make up
```

Brings up all five services. `docker-compose.override.yml` is applied
automatically and gives `backend`/`frontend` live reload against your
local source.

## Backend, running directly on the host (no Docker)

Needed for `alembic revision --autogenerate` (it needs `uv`/Python on the
host) and is the faster loop for `pytest`.

```bash
cd backend
uv sync
docker compose up -d postgres redis chromadb   # from repo root, or via make
uv run alembic upgrade head
uv run pytest
```

Host-side tools (`alembic`, `pytest`) read `backend/.env` (gitignored,
**not** the root `.env`), because they connect via `localhost:<published
port>`, not the in-network service DNS names (`postgres`, `redis`,
`chromadb`) the containers use. Create it from `backend/.env.example` if
it's missing:

```bash
cp backend/.env.example backend/.env
```

## Migrations

```bash
cd backend
uv run alembic revision --autogenerate -m "<description>"   # needs postgres running
uv run alembic upgrade head
uv run alembic downgrade -1                                    # roll back one
```

`docker compose up` never runs migrations itself — a fresh `postgres`
volume has no schema until you apply them, or every request 500s with
`relation "..." does not exist`. Containerized equivalent (also `make
migrate`):

```bash
docker compose exec backend alembic upgrade head
```

No `uv run` prefix — the `backend` service runs the `runtime` Dockerfile
stage, which has the app's venv (and therefore `alembic`, a real
dependency, not dev-only) on `PATH` but deliberately doesn't have `uv`
itself (that's only in the `builder`/`test` stages — see "Production
deployment" below for why that distinction matters).

CI (`.github/workflows/ci.yml`'s `compose-integration` job) does this
explicitly before running the e2e suite against a stack it just brought
up from scratch.

Postgres `ENUM` types (`document_status`, `study_kit_type` today) aren't
dropped automatically when their table is dropped — SQLAlchemy/Alembic
autogenerate emits `DROP TABLE` but not `DROP TYPE`. Every downgrade that
drops a table with an `Enum` column needs an explicit
`sa.Enum(name="...").drop(op.get_bind(), checkfirst=True)` added after the
`op.drop_table(...)` call, or the next `upgrade` fails with `type "..."
already exists`. Check generated migrations for this before committing
them.

## Tests

`backend/tests/conftest.py` creates a dedicated `<database>_test` Postgres
database per test session (never touches your dev data), applies
`Base.metadata.create_all` once, and wraps each test in a transaction +
savepoint that's rolled back afterward — tests can `commit()` freely
without leaking state into the next test. Requires `postgres`, `redis`,
and (since Phase 2) `chromadb` reachable — `make up` or
`docker compose up -d postgres redis chromadb` covers all three.

```bash
cd backend && uv run pytest
```

No test calls live Ollama Cloud by default — ingestion tests use a
`FakeLLMClient` (`tests/conftest.py`), so `OLLAMA_API_KEY` isn't needed to
run the suite. See [ingestion.md](ingestion.md) for what that does and
doesn't cover.

`tests/live/` is the one exception: real round-trips against whatever
Ollama endpoint `.env` points at, marked `live_model` and excluded by
default (`addopts = "-m 'not live_model'"` in `pyproject.toml`). Run them
deliberately, with a real endpoint reachable:

```bash
cd backend && RUN_LIVE_LLM_TESTS=1 uv run pytest -m live_model
```

A schema-validation failure there is a real signal about the target
endpoint's `response_format` fidelity, not flakiness — see `TODO.md`
Phase 2 follow-ups.

`tests/e2e/` is a third kind: real HTTP against the actual running
`backend` container — not `ASGITransport`, not an in-process app object —
so it catches what those can't (real Docker networking, real uvicorn, a
missing env var inside the container). Marked `e2e`, excluded by default
(`addopts` also excludes `e2e`). Run via the `test` Docker Compose
profile, which builds `backend`'s `test` image stage (`Dockerfile`'s
`builder` stage plus dev dependencies — `pytest` isn't in the deployed
`runtime` image) and runs it against the real `backend` service:

```bash
docker compose up -d
docker compose --profile test run --rm backend-tests
```

No live Ollama needed — `tests/e2e/` only exercises routes that don't
call the model (auth, ownership scoping, deterministic recommendation).

## Coverage and type-checking

```bash
cd backend
uv run pytest --cov=src/domain --cov=src/agents --cov-report=term-missing --cov-fail-under=80
uv run pyright
```

`[tool.coverage.run]` in `pyproject.toml` sets `concurrency = ["greenlet",
"thread"]` — without it, coverage doesn't trace into the greenlet
SQLAlchemy's async dialects run queries in, and everything after an
`await db.scalar(...)` et al. reads as "missed" even when a test runs it.
`pyright` runs in `basic` mode (`backend/pyrightconfig.json`); a handful
of remaining findings are suppressed inline with a one-line reason each
(mostly chromadb-client/redis-py/python-docx/python-pptx stub gaps, plus
LangGraph's intentionally-partial `AgentState` in `agents/graph.py`).

## CI

`.github/workflows/ci.yml` runs on every PR and on push to `main`:
`backend-lint` → `backend-type-check` → `backend-test` (coverage gate) →
`frontend-lint-type-check` → `docker-build` → `compose-integration` (the
full five-service `docker compose up`, migrated, then `tests/e2e/`
against it — the same commands as the sections above, run by a machine
instead of by hand).

## Load testing

`backend/load-tests/` — k6 against `GET /recommendation/next` and `POST
/study-kit/generate`, the two endpoints `plan.md`'s KPI table sets
latency targets on. See `backend/load-tests/README.md` for how to run it
and what it does and doesn't measure without a live Ollama endpoint.

## Production deployment

```bash
cp .env.example .env   # then edit it — see the checklist below
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend alembic upgrade head
```

Before that first `up`, in `.env`:

- **`JWT_SECRET`** — a real random value (`openssl rand -hex 32`). The
  backend logs a startup warning and every token stays forgeable if this
  is still `change-me`.
- **`CORS_ALLOWED_ORIGINS`** — the real frontend origin(s) the browser
  will call the API from, not the `localhost` dev defaults.
- **`NEXT_PUBLIC_API_URL`** — the real public backend URL; it's baked
  into the frontend at build time (Next.js inlines `NEXT_PUBLIC_*` env
  vars into the client bundle), so it must be set correctly *before*
  `--build`, not adjusted after.
- **`OLLAMA_API_KEY`** — a real Ollama Cloud key, unless deliberately
  running against a self-hosted Ollama instead.
- **Postgres/Redis credentials** — real values, not the `change-me`
  defaults.

`docker-compose.prod.yml` never merges automatically — see
`architecture.md` → "Local vs. production compose" for exactly what it
changes and why it's a separate file `-f`'d in explicitly rather than
another auto-applied override. Migrations still need the explicit
`alembic upgrade head` step (above) — nothing in either compose file
runs them automatically, on a fresh volume or an upgrade alike.

There's no CD here — this is "how to bring the stack up correctly", not
a deployment pipeline. Wiring this into a real host (or ECS/Fargate/EKS,
per `TODO.md` Phase 7's alternative) is out of this project's scope so
far.

## Common failures

**`role "learn_buddy" does not exist` from `alembic`/`pytest`, but `docker
exec ... psql` into the same container works fine.** Something else on the
host is already listening on `127.0.0.1:5432` (a Homebrew/system Postgres
is the usual culprit) and is shadowing the Docker container's published
port for connections to `localhost`. Confirm with `lsof -nP -iTCP:5432
-sTCP:LISTEN`; if two processes are listed, change `POSTGRES_PORT` in the
root `.env` (e.g. `5433`) and update `backend/.env`'s `DATABASE_URL` to
match, then `docker compose up -d postgres` to rebind.

**`RuntimeError: Task ... got Future ... attached to a different loop`**
in async DB tests. A session-scoped async fixture (e.g. the test engine)
got created on a different event loop than the per-test one. Fixed via
`asyncio_default_fixture_loop_scope = "session"` **and**
`asyncio_default_test_loop_scope = "session"` in `pyproject.toml`'s
`[tool.pytest.ini_options]` — both are required; the fixture-scope setting
alone isn't enough.

**A test hitting an intentionally-raised 500 sees the exception instead of
the `{code, message}` response.** Starlette's `ServerErrorMiddleware`
always re-raises after sending the response (so real servers can log it).
`httpx.ASGITransport` re-raises that to the caller by default
(`raise_app_exceptions=True`). Pass `raise_app_exceptions=False` to
`ASGITransport` in that specific test.

**Uploads accept the file but the document sits at (or ends at)
`status: FAILED`.** Upload itself isn't the failure point — it's
background ingestion, which runs after the HTTP response. Two known
causes, check backend logs (`docker compose logs backend`) for which:

1. `LLMError: Ollama request failed: All connection attempts failed` —
   nothing is listening at `OLLAMA_BASE_URL` (`.env`). If it points at
   `http://host.docker.internal:11434` (local dev default), start Ollama
   on the host with `ollama serve` and confirm `curl
   http://localhost:11434/api/tags` responds before retrying the upload.
2. `Model output did not match <Schema>` from `topic_extractor` /
   `classify` / `study_kit` — see
   [decisions/0010-json-object-mode-for-structured-output.md](decisions/0010-json-object-mode-for-structured-output.md).
   If this resurfaces after an Ollama/model upgrade, that ADR's fix may
   need revisiting rather than being the permanent answer.
