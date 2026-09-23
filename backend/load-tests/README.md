# Load tests

k6 load test for the two endpoints `wiki/plan.md`'s KPI table sets
latency targets on: `GET /recommendation/next` (< 3s p95) and
`POST /study-kit/generate` (< 15s p95, cold).

## Run

```bash
brew install k6   # or see https://k6.io/docs/get-started/installation/

cd backend
docker compose exec backend uv run alembic upgrade head   # schema must exist
PYTHONPATH=. uv run python load-tests/seed.py               # 50 students + topics, no ingested material
cd load-tests
k6 run recommendation_and_study_kit.js
```

`BASE_URL` (default `http://localhost:8000`), `DURATION` (default `30s`),
`RECOMMENDATION_VUS` (default `10`), and `STUDY_KIT_VUS` (default `5`) are
all overridable via `--env`, e.g. `k6 run --env DURATION=2m ...`.

`seed.py` writes real JWTs to `seed-data.json` (gitignored) — delete the
seeded `load-test-*@example.com` students afterward if you're running
against a shared database, not just local dev.

## What this does and doesn't measure

`seed.py` creates students and topics directly in Postgres — no ingested
Chroma chunks, and no live Ollama call — so `POST /study-kit/generate`
hits its retrieval guardrail (`NotCovered`, see `agent-design.md`) or the
rate limiter (`429`, expected and treated as a pass, not a failure — see
the script's threshold comments) almost immediately, never the model.
That's still a real, meaningful number: it's this endpoint's fully-loaded
latency *floor* — DB queries, Chroma's empty-collection check, auth,
rate-limit bookkeeping — with zero LLM time added on top.

It is **not** a measurement of real generation latency against Ollama
Cloud, which needs actual ingested material and a real `OLLAMA_API_KEY`
— neither available in every environment this runs in. To get that
number: ingest real documents for the seeded students first (via the
actual `/documents/upload` flow, not `seed.py`), with a real Ollama
credential configured, then rerun. Same "live model needed, not always
available" gap as `tests/live/` — see `wiki/runbook.md`.

## Results (this environment, no live LLM, 2026-09-23)

20s per scenario, 10 VUs (`recommendation`) / 5 VUs (`study_kit_generate`):

| Endpoint | p95 | Target | Result |
| --- | --- | --- | --- |
| `GET /recommendation/next` | 46ms | < 3000ms | comfortably clears — pure DB logic, no LLM in this path at all |
| `POST /study-kit/generate` | 49ms | < 15000ms (cold) | clears, but see "What this does and doesn't measure" — this is the guardrail/rate-limit floor, not a real generation number |
