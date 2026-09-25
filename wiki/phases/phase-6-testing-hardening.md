# Phase 6 — Testing, Observability & Hardening

## Goal

Raise confidence the system is production-ready without adding new
product surface: close backend test coverage on `domain/` and `agents/`
to the ≥80% target, stand up CI (lint, type-check, test, docker build,
and a full five-service `docker compose` integration run) so every PR is
checked the same way a human would check it locally, run a real security
pass (JWT behavior, PII-in-logs, per-student scoping) and fix what it
finds, and load-test the two endpoints `wiki/plan.md` sets latency KPIs
on.

## What was built

- **Coverage**: `pytest-cov` added; `domain/` + `agents/` at 99%
  (`domain/documents.py`, `study_kits.py`, `topics.py` were the weak
  spots — new tests under `tests/domain/`, plus a few more in
  `tests/agents/test_graph.py` and a new `tests/agents/test_quiz_grading.py`).
  A real measurement bug surfaced first: default `coverage.py` doesn't
  trace into the greenlet SQLAlchemy's async dialects spawn for every
  query, so every line after an `await db.scalar(...)` et al. read as
  "missed" even when the test suite ran it — fixed with `concurrency =
  ["greenlet", "thread"]` in `pyproject.toml`'s `[tool.coverage.run]`,
  which is what took the *measured* number from a misleading 90% to the
  real 97% before any test was even added. Also removed
  `domain.documents.mark_status` — dead code, never called (`ingestion/
  pipeline.py` sets `document.status` directly).
- **`pyright`** added (`basic` mode, `backend/pyrightconfig.json`) as the
  "type-check" pipeline stage `TODO.md` asks for — ruff doesn't do this.
  Found and fixed two real gaps (`core/cache.py`'s `get()` return type
  not accounting for `decode_responses=True`; `ingestion/parsers/docx.py`
  not handling a style with no `.name`) and suppressed the rest, which
  are all third-party stub imprecision (chromadb-client, redis-py,
  python-docx, python-pptx) or LangGraph's intentionally-partial
  `AgentState` — each with an inline justification, not a blanket
  file-level disable.
- **`.github/workflows/ci.yml`**: `backend-lint`, `backend-type-check`,
  `backend-test` (coverage gate, `--cov-fail-under=80`),
  `frontend-lint-type-check` (lint, `tsc --noEmit`, `next build`),
  `docker-build` (all three image stages), and `compose-integration` —
  brings up all five services from a cold `docker compose up --build`,
  waits for real health, applies migrations, then runs `tests/e2e/`
  against the actual containers. Every job's commands were run by hand
  against this repo before being trusted in the workflow file — see
  "Harder than expected".
- **Security pass** (`core/errors.py`, `main.py`): found and fixed a real
  one — `RequestValidationError`'s default `.errors()` echoes the raw
  submitted value back in the response body, so a too-short `password`
  on `/auth/register` came back in the 422 verbatim. Stripped `input`
  from every validation error, not just password fields. Also added a
  startup warning if `JWT_SECRET` is still the `change-me` placeholder.
  Everything else audited clean: no email/password/quiz-answer content
  anywhere in `logger.*` calls (every log uses ids, never PII); every
  domain query that reads one student's data is scoped by `student_id`
  either directly or transitively through an already-ownership-checked
  parent (audited file by file — see `architecture.md` → "Security");
  JWT expiry/rotation/blacklist already had coverage from Phases 1 and 4.
- **`load-tests/`** (k6 + a direct-to-Postgres seed script): both KPI
  endpoints clear their p95 targets by two orders of magnitude in this
  environment — but see `load-tests/README.md` → "What this does and
  doesn't measure": no live Ollama here means `/study-kit/generate` is
  only measured on its guardrail/rate-limit floor, not real generation
  latency.

## Harder than expected

The CI workflow looked complete on paper and broke on the first real dry
run: a fresh `docker compose up` stack has no Postgres schema (nothing
runs migrations automatically), so every `compose-integration` request
would have 500'd with `relation "..." does not exist` — caught only by
actually running `docker compose up` on a torn-down (`-v`) stack by hand
and watching the e2e suite fail, not by reading the YAML. Fixed by adding
an explicit `alembic upgrade head` step; `wiki/runbook.md` now calls this
out too, since it's just as true for a human running `docker compose up`
fresh as it is for CI.

The coverage-measurement gap (above) was the same lesson from a different
angle: the tool reported a plausible-looking number (90%) that was wrong
in a specific, structural way (every post-`await` line in an
async-SQLAlchemy call), and it would have been easy to "fix" by writing
redundant tests for lines that were already covered, instead of fixing
the measurement itself.

## Deviations from the plan

None beyond what's noted above — this phase's scope matched `TODO.md`
closely. The "cached" half of `/study-kit/generate`'s KPI
(`< 5s p95 cached`) doesn't apply: nothing in the system caches
generation results (each call is a fresh model call by design, see
`wiki/agent-design.md`), so only the "cold" target is meaningful against
the current implementation.
