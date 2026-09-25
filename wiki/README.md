# Learn Buddy Wiki

Index of everything in `wiki/`. Living pages describe the current system;
`phases/` are historical build logs; `decisions/` are ADRs.

| Page | Summary |
| --- | --- |
| [architecture.md](architecture.md) | System diagram, Docker services, and the backend's and frontend's internal package layout. |
| [data-model.md](data-model.md) | ER diagram and table-by-table description of the Postgres schema. |
| [ingestion.md](ingestion.md) | The upload → parse → chunk → embed → topic-extract pipeline. |
| [agent-design.md](agent-design.md) | The LangGraph agent graph: classification, retrieval, the action nodes (topic chat, Feynman-mode grading, worked-answer grading), guardrails. |
| [api-reference.md](api-reference.md) | Every route: auth, request/response shape, rate limiting. |
| [runbook.md](runbook.md) | How to run locally (Docker and host-direct), migrations, tests, common failures. |
| [plan.md](plan.md) | Original project plan (objectives, requirements, KPIs, roadmap). |
| [phases/phase-0-docker-foundation.md](phases/phase-0-docker-foundation.md) | Docker Compose skeleton for all five services; what was built and why. |
| [phases/phase-1-backend-foundations.md](phases/phase-1-backend-foundations.md) | `backend/src/` layout, data model, auth, error envelope, logging, test scaffold. |
| [phases/phase-2-ingestion.md](phases/phase-2-ingestion.md) | Upload endpoint, parsers, chunker, Ollama client, topic extraction, idempotent re-upload. |
| [phases/phase-3-agentic-core.md](phases/phase-3-agentic-core.md) | LangGraph agent: classifier, retrieval, recommend/study-kit/mastery/remediation nodes. |
| [phases/phase-4-api-layer.md](phases/phase-4-api-layer.md) | Auth, documents/graph/progress/recommendation/study-kit/quiz routers, rate limiting, e2e test profile. |
| [phases/phase-5-frontend.md](phases/phase-5-frontend.md) | Next.js UI: auth, upload, dashboard, four study-kit views, design tokens. |
| [phases/phase-6-testing-hardening.md](phases/phase-6-testing-hardening.md) | Coverage, pyright, CI pipeline, security pass, k6 load test. |
| [phases/phase-7-deployment-docs.md](phases/phase-7-deployment-docs.md) | Production compose overlay, the default-build-target bug it surfaced, final wiki/README pass. |
| [decisions/0001-ruff-as-dev-dependency.md](decisions/0001-ruff-as-dev-dependency.md) | Why `ruff` was added as a backend dev dependency in Phase 0. |
| [decisions/0002-thin-chroma-client.md](decisions/0002-thin-chroma-client.md) | Why `chromadb-client==0.5.20`, not the full `chromadb` package. |
| [decisions/0003-reupload-replaces-topics.md](decisions/0003-reupload-replaces-topics.md) | Why re-upload fully replaces a document's topics instead of merging. |
| [decisions/0004-background-tasks-not-a-queue.md](decisions/0004-background-tasks-not-a-queue.md) | Why ingestion runs via FastAPI `BackgroundTasks`, not Celery/RQ. |
| [decisions/0005-cosine-similarity-for-retrieval-guardrail.md](decisions/0005-cosine-similarity-for-retrieval-guardrail.md) | Why retrieval's Chroma collections use cosine space, not the default L2. |
| [decisions/0006-deterministic-justification-text.md](decisions/0006-deterministic-justification-text.md) | Why recommendation/remediation text is composed, not model-generated. |
| [decisions/0007-server-side-quiz-grading.md](decisions/0007-server-side-quiz-grading.md) | Why `POST /quiz/submit` grades server-side instead of trusting a client score. |
| [decisions/0008-localstorage-jwt-spa-auth.md](decisions/0008-localstorage-jwt-spa-auth.md) | Why the frontend uses localStorage JWTs and client components instead of cookies + Proxy. |
| [decisions/0009-pin-docker-build-target.md](decisions/0009-pin-docker-build-target.md) | Why `target: runtime` is pinned explicitly, and the bug that made it necessary. |
| [decisions/0010-json-object-mode-for-structured-output.md](decisions/0010-json-object-mode-for-structured-output.md) | Why `chat_json` uses `json_object` mode with an inline schema instruction instead of `json_schema` strict mode. |
| [decisions/0011-study-ledger-visual-redesign.md](decisions/0011-study-ledger-visual-redesign.md) | Why the frontend was redesigned around a single dark "Study Ledger" theme instead of the original indigo light/dark palette. |
| [decisions/0012-topic-chat-guardrails.md](decisions/0012-topic-chat-guardrails.md) | Why topic chat scopes retrieval to one document *and* adds a model self-refusal guardrail on top of the coverage threshold. |
| [decisions/0013-sidebar-topbar-app-shell.md](decisions/0013-sidebar-topbar-app-shell.md) | Why the hero masthead was replaced with a persistent sidebar + top bar app shell. |
| [decisions/0014-feynman-and-worked-answer-grading.md](decisions/0014-feynman-and-worked-answer-grading.md) | Why Feynman-mode and worked-answer grading share `apply_mastery_observation` with quizzes, and why worked-answer grading skips retrieval. |
