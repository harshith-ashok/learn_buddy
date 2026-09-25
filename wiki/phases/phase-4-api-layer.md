# Phase 4 — API Layer

## Goal

Expose the domain and agent logic built in Phases 1–3 as a real HTTP API:
routers for documents, the topic graph, progress, recommendation, study
kit generation, and quiz submission, each a thin controller over
`domain/`/`agents/` — Pydantic request/response schemas throughout,
consistent auth and per-student query scoping, rate limiting on the one
endpoint that calls the LLM to generate new content, and API-level tests
driving it all through real HTTP calls.

## What was built

- **`api/auth.py`** — `/auth/register`, `/login`, `/refresh`, `/logout`.
  Not in `TODO.md`'s Phase 4 router list, but nothing else in the plan
  ever exposed a way to obtain a token — Phase 1 built the JWT mechanism
  assuming a caller later would. Refresh tokens rotate: `/refresh`
  blacklists the presented token's `jti` in Redis (TTL'd to its remaining
  validity) and issues a fresh pair, so it can't be replayed.
- **`api/documents.py`** — added `GET /documents` (list) and `GET
  /documents/{id}` alongside the existing Phase 2 upload endpoint, both
  thin wrappers over `domain.documents`.
- **`api/graph.py`**, **`domain/topics.py: get_course_graph`** — the full
  topic graph (subtopics, prerequisite edges, per-student mastery) for
  one document, assembled in one domain function so the route stays a
  pure response-shaping wrapper.
- **`api/progress.py`**, **`domain/progress.py`** — mastery across every
  ingested topic, `LEFT JOIN`ed against `mastery_scores` so an unscored
  topic reports `0.0` rather than being missing from the list.
- **`api/recommendation.py`** — a direct pass-through to
  `agents.recommend.recommend_next_topic`; the response model is
  `Recommendation | NoRecommendation` from `agents.schemas` itself,
  reused rather than duplicated.
- **`api/study_kit.py`** — generation, rate-limited via
  `api/deps.py: rate_limiter` (`STUDY_KIT_GENERATION_RATE_LIMIT` per
  `..._WINDOW_SECONDS`), the only route that calls the model for new
  content.
- **`api/quiz.py`**, **`agents/quiz_grading.py`**,
  **`domain/study_kits.py`** — grades a submission server-side against
  the quiz's own stored answers rather than trusting a client-supplied
  score (`agents.schemas.QuizSubmission.score` was a Phase 3 internal
  field, never meant to be client input) — see
  [decisions/0007](../decisions/0007-server-side-quiz-grading.md). Fires
  `trigger_remediation` automatically when `score_and_update_mastery`
  says to.
- **`api/deps.py`** additions: `CacheDep`, and `rate_limiter(scope,
  limit, window_seconds)` — a dependency factory over
  `CacheClient.incr_with_ttl`, its limit resolved once from `Settings` at
  router-construction time (matches how the rest of the app treats
  config: fixed for the process's lifetime, not hot-reloadable).
- **`core/errors.py: RateLimitedError`** (429).
- **`tests/api/`**: `test_auth.py`, `test_graph.py`, `test_progress.py`,
  `test_recommendation.py`, `test_study_kit.py`, `test_quiz.py` — 22 new
  tests, in-process (`ASGITransport`), fake LLM client, real
  Postgres/Chroma/Redis. `FakeAgentLLMClient` moved from
  `tests/agents/conftest.py` to the root `tests/conftest.py` so both
  `tests/agents/` and `tests/api/` can use it.
- **`tests/e2e/`** — real HTTP tests against the actual running `backend`
  container, driven by a new Docker Compose `test` profile
  (`backend-tests` service, `Dockerfile`'s new `test` stage — the
  `builder` stage plus dev dependencies, since the deployed `runtime`
  image deliberately has no `pytest`). Required removing `tests` from
  `backend/.dockerignore`, so test files now ride along in the built
  image (a small, accepted tradeoff — see "Deviations" below).

## Harder than expected

`backend/.dockerignore` excluded `tests/` from every build context, so
the first `backend-tests` run built successfully but failed with `file or
directory not found: tests/e2e` — the directory the "test" stage's `CMD`
pointed at had never been copied in. Not obvious until actually running
the container; a review of the Dockerfile alone wouldn't have caught it,
since `COPY . .` looks complete without checking what the ignore file
excludes.

## Deviations from the plan

- `api/auth.py` isn't in `TODO.md`'s Phase 4 router list (see above) —
  added because the plan has no other point where it could go.
- `TODO.md`'s "API-level tests hitting the running backend container
  through docker-compose's test profile" needed a Docker Compose
  `profiles: ["test"]` service and a new Dockerfile stage, neither of
  which existed — both added as part of this phase, not a prerequisite
  assumed already in place.
- Removing `tests` from `.dockerignore` means the deployed `runtime`
  image also carries `tests/` now (both stages share the same `builder`
  base). Accepted for now — a leaner split (separate build contexts, or
  excluding `tests/` again just for the `runtime` `COPY --from=builder`)
  is a Phase 7 (deployment hardening) concern, not this phase's.

## Follow-up: quiz-answer leak, found building the Phase 5 quiz view

`GET`/`POST /study-kit/*` originally returned a quiz's `content` (and
therefore `correct_index`) verbatim. Fixed:
`api/study_kit.py: _redact_quiz_answers` strips `correct_index` from
every quiz response this API ever returns; grading is unaffected since
it reads `study_kits.content` from the database directly (see
[decisions/0007](../decisions/0007-server-side-quiz-grading.md)). Also
added `GET /study-kit?topic_id=` and `GET /study-kit/{id}` — not in
`TODO.md`'s Phase 4 list, needed so the Phase 5 frontend can redisplay a
previously generated kit.

## Follow-up: `backend`'s default Docker build target, found in Phase 7

Adding the `test` stage (above) after `runtime` meant every build
without an explicit target silently built `test`, not `runtime` —
invisible in dev (the override file's explicit `command:` masked it) the
whole time since. Fixed in Phase 7 —
[decisions/0009](../decisions/0009-pin-docker-build-target.md).
