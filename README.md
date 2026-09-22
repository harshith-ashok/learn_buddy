# Learn Buddy

Personalized Learning Path Generator: turns an uploaded syllabus into a
topic/subtopic knowledge graph, tracks per-topic mastery, and always tells
the learner the single highest-value next study action — generating
summaries, flashcards, quizzes, or problem guides on demand, grounded in the
learner's own materials.

Full plan: [wiki/plan.md](wiki/plan.md). Living docs: [wiki/README.md](wiki/README.md).

## Architecture

Five independent Docker services, one per concern — no monolith container:

| Service    | Role                                                        |
| ---------- | ----------------------------------------------------------- |
| `frontend` | Next.js UI                                                  |
| `backend`  | FastAPI app: API layer, agent orchestration                 |
| `postgres` | Relational store: users, knowledge graph, progress, mastery |
| `redis`    | Session state, rate limiting, short-lived agent memory      |
| `chromadb` | Vector store for retrieval-augmented generation             |

The LLM is Ollama Cloud (`gpt-oss:120b-cloud`), called over HTTPS — there is
no `ollama` container. See [wiki/architecture.md](wiki/architecture.md) for
the current component diagram.

## Use of AI

AI assistance was used during development to help plan the architecture,
scaffold backend and frontend code, debug implementation issues, write and
refine backend tests, and prepare the Docker and wiki documentation. Generated
suggestions were reviewed, adapted to the project's conventions, and verified
with the test, lint, type-check, and Docker workflows before being kept.

## Local setup

Requires Docker and Docker Compose.

```bash
cp .env.example .env   # fill in OLLAMA_API_KEY and any secrets you need
make up                 # builds and starts all five services
make migrate             # applies the Postgres schema — needed once, and after every new migration
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000 (health check at `/health`, docs at `/docs`)
- Postgres: localhost:5432, Redis: localhost:6379, Chroma: localhost:8001

`make up` never runs migrations itself — skip `make migrate` and every
API call that touches the database 500s with `relation "..." does not
exist`.

`docker-compose.override.yml` is applied automatically and gives the
`backend` and `frontend` containers live-reload against your local source —
no rebuild needed while iterating.

Other common commands:

```bash
make down        # stop all services
make logs        # tail logs from all services
make test        # backend pytest + the e2e profile against the live containers + frontend tests
make migrate     # run Alembic migrations against the running backend
make lint        # ruff (backend) + eslint (frontend)
make type-check  # pyright (backend) + tsc --noEmit (frontend)
```

Running the backend directly on the host (e.g. for `alembic revision
--autogenerate` or a faster `pytest` loop) needs its own `backend/.env` —
see [wiki/runbook.md](wiki/runbook.md).

## Production

```bash
cp .env.example .env   # then set JWT_SECRET, CORS_ALLOWED_ORIGINS, NEXT_PUBLIC_API_URL, etc. for real
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend alembic upgrade head
```

No dev bind-mounts, resource limits per service, datastores not exposed
to the host. See [wiki/runbook.md](wiki/runbook.md) → "Production
deployment" for the full checklist before that first `up`.

## Testing

Backend behavior is covered with `pytest`, including unit, API, agent, domain,
ingestion, database, and end-to-end tests. Run the backend suite directly with:

```bash
cd backend
uv run pytest
```

The root `make test` command also runs the backend suite, live-container e2e
tests, and frontend tests.

## Docker deployment and documentation

Docker Compose runs the frontend, backend, Postgres, Redis, and Chroma as
separate services. Use the development override for live reload, or the
production overlay for a build without development bind mounts:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

The [wiki](wiki/README.md) is the living project documentation, with pages for
architecture, data model, agent design, API reference, runbook, decisions,
and phase notes.

## Repo layout

```
backend/    FastAPI app (uv-managed) — see backend/README.md
frontend/   Next.js app — see frontend/README.md
wiki/       living docs, ADRs, and per-phase build notes
```

For anything deeper than this — data model, agent design, API reference,
runbook, and decisions — see [wiki/README.md](wiki/README.md).
