# Phase 2 — Ingestion Pipeline & Knowledge Graph

**Goal** (from `TODO.md`): an upload endpoint that stores a syllabus and
enqueues processing; format parsers normalized to one `ParsedDocument`
structure; a heading-aware chunker; an embedding step writing to Chroma;
LLM-driven topic/subtopic extraction writing to Postgres; idempotent
re-upload; an integration test proving topic/chunk counts out of a
fixture syllabus.

## What was built

- **`POST /documents/upload`** (`api/documents.py`) — validates extension
  and size, hashes the bytes, stores them
  (`ingestion/storage.py`, keyed by `(student_id, content_hash)`),
  upserts a `documents` row (`domain/documents.py`), and schedules
  `ingestion.pipeline.process_document` as a `BackgroundTasks` job. See
  [decisions/0004](../decisions/0004-background-tasks-not-a-queue.md) for
  why that's `BackgroundTasks` rather than a Celery/RQ worker.
- **Parsers** (`ingestion/parsers/{pdf,docx,pptx}.py`) — each normalizes
  to `ParsedDocument`/`ParsedSection` (`ingestion/schemas.py`). DOCX gets a
  real nested heading tree from its paragraph styles (including tables,
  attached to whichever section is open when they appear); PPTX and PDF
  are flat (one section per slide/page — see `wiki/ingestion.md` for why
  PDF heading detection isn't attempted for real).
- **Chunker** (`ingestion/chunker.py`) — DFS over the section tree,
  ~400-word chunks (word count as a token-count proxy) with 50-word
  overlap, never crossing a heading boundary. Unit-tested against the
  three required edge cases (no headings, very short docs, table-shaped
  text) plus overlap correctness and document-order chunk ids.
- **`core/llm_client.py`** — the one Ollama Cloud client (per
  `CLAUDE.md`), OpenAI-compatible endpoints, `embed()` and `chat_json()`
  (JSON-schema-constrained, Pydantic-validated on receipt), retries with
  backoff on 429/5xx, no retry on 4xx. Fully unit-tested against a mocked
  transport (`httpx.MockTransport`) — no live model calls anywhere in the
  suite.
- **Embedder** (`ingestion/embedder.py`) — batches chunks through
  `embed()`, upserts into a per-student Chroma collection
  (`core/vectorstore.py`), clearing that document's prior entries first
  (idempotent re-embed).
- **Topic extractor** (`ingestion/topic_extractor.py`) — one `chat_json`
  call constrained to `TopicExtractionResult`, prompted with a bounded
  document outline (headings + excerpts, capped at 8000 chars, not full
  chunk text). `persist_topics` writes `topics`/`subtopics` and resolves
  `prerequisites` (by name, within the same result) to
  `topic_prerequisites` edges, dropping and logging any dangling or
  self-referential reference.
- **Pipeline** (`ingestion/pipeline.py`) — orchestrates
  parse → chunk → embed → extract → persist, sets `document.status`
  through `PROCESSING`/`DONE`/`FAILED`, and (on re-upload) fully replaces
  the document's prior topics before writing the new extraction. See
  [decisions/0003](../decisions/0003-reupload-replaces-topics.md) for why
  that's a replace, not a merge, and what it costs.
- **Dependency injection for testability**: the upload route depends on
  `LLMClientDep`, `VectorStoreDep`, and a new `SessionFactoryDep`
  (`api/deps.py`, `db/session.py: get_session_factory`), all passed
  explicitly into the background job instead of the job reaching for
  module-level singletons. This is what let the integration test drive
  the real endpoint end-to-end with a fake LLM client and an isolated (but
  real) Chroma collection, reusing the test's own transactional DB
  session for the background job.
- **`backend_uploads` Docker volume** — raw uploaded files persist at
  `STORAGE_DIR` (`/app/storage` in-container) across container restarts.
- 34 new tests across `tests/ingestion/` (parsers, chunker, storage,
  embedder, topic extractor) and `tests/api/test_documents.py` (the full
  upload → pipeline → persisted-rows integration test, plus
  unsupported-format and auth-required cases).

## What a new engineer needs to know

- **The background-task session bug, and its fix.** The first version of
  `process_document` opened its own DB session from a module-level
  `async_session_factory` — which, in tests, silently pointed at a
  *different* database than the test's isolated `<db>_test` transaction.
  The background task would run, find no matching document, log an error,
  and return — no exception, no obviously-failing assertion, just topics
  that silently never appeared. Fixed by making the session factory an
  injectable FastAPI dependency (`SessionFactoryDep`) like the LLM client
  and vectorstore already were, so tests can point it at their own
  transaction. Worth remembering if a future background job is added the
  same naive way.
- `chromadb-client==0.5.20`'s `list_collections()` returns `Collection`
  objects (`.name`), not bare strings — used in test teardown
  (`tests/conftest.py: test_vectorstore`) to clean up per-test Chroma
  collections.
- `FastAPI`'s `BackgroundTasks` genuinely run to completion (or raise)
  *before* an in-process ASGI call (like httpx's `ASGITransport`, which
  the whole test suite runs on) returns control to the caller — this is
  what makes `tests/api/test_documents.py` able to assert on the
  pipeline's results immediately after `await client.post(...)`, with no
  polling or sleep.
- Token counts everywhere in the chunker are word counts, not a real
  tokenizer's token count — deliberate (model-agnostic, no tokenizer
  dependency), documented in `ingestion/chunker.py` and `wiki/ingestion.md`.
- **Test isolation gap, also found and fixed**: the upload route reads
  `storage_dir` off the real, process-wide `Settings` singleton — nothing
  about the DB/LLM/vectorstore dependency overrides touches it, so the
  first integration test runs wrote real files under `backend/storage/`
  in the repo working tree. Fixed with a session-scoped, autouse
  `_isolated_storage_dir` fixture (`tests/conftest.py`) that redirects it
  to a temp dir before any test runs; `backend/storage/` is also now
  gitignored as a backstop.
- No live-model smoke test exists yet (no `OLLAMA_API_KEY` was available
  in this environment). Everything is verified against a `FakeLLMClient`;
  the `core/llm_client.py` HTTP contract itself is verified against a
  mocked transport, not a real Ollama Cloud call. Phase 3 already plans a
  "one live-model smoke test behind a separate marker" — worth adding a
  matching one for ingestion when a real key is available.

## Verification

`uv run pytest` — 47 passed (up from 13 after Phase 1), including the
integration test asserting exact topic and chunk counts from a
programmatically-built fixture syllabus. `ruff format` + `ruff check`
clean. Rebuilt the Docker image (new deps: `pypdf`, `python-docx`,
`python-pptx`, `python-multipart`, `httpx`, `chromadb-client`) —
`docker compose up -d --build` brings all five services up healthy again;
confirmed the new `backend_uploads` volume is created and mounted, and
that `POST /documents/upload` against the live container correctly
returns the `{code, message}` envelope for an unauthenticated request.
Did not attempt a real upload against the live container, since that
needs a real `OLLAMA_API_KEY` this environment doesn't have.

## Deviations from the plan

- Added a `SessionFactoryDep` dependency and `db/session.py:
  get_session_factory` — not asked for by `TODO.md`, but required once
  the upload endpoint needed to hand real, injectable dependencies to a
  background job (see above).
- `TODO.md` doesn't specify how "enqueues processing" should be
  implemented; used FastAPI `BackgroundTasks` rather than standing up a
  Celery/RQ worker — see
  [decisions/0004](../decisions/0004-background-tasks-not-a-queue.md).
- `TODO.md` doesn't specify merge-vs-replace semantics for topics on
  re-upload beyond "updates existing... instead of duplicating"; chose
  full replace — see
  [decisions/0003](../decisions/0003-reupload-replaces-topics.md).

## Footnote: first real-model run, after this phase landed

Once a local Ollama became available (`OLLAMA_BASE_URL=http://localhost:11434`
outside Docker, `http://host.docker.internal:11434` from the `backend`
container — `localhost` there means the container itself), running
`core/llm_client.py` against it for the first time surfaced two real bugs,
now fixed and covered by new unit tests:

1. With no `OLLAMA_API_KEY`, the client sent `Authorization: Bearer `
   (trailing space, nothing after it) on every request — an illegal
   header value that `httpx`/`h11` reject at send time, not construction
   time, so it passed silently until a real request was made. Fixed: no
   `Authorization` header at all when there's no key.
2. `chat_json()` failed to parse a real response wrapped in a
   ` ```json ... ``` ` fence. Fixed with `_strip_markdown_fence` — a
   formatting correction applied before `json.loads`, not a free-text
   parse (the result still goes through the same strict schema
   validation).

`embed()` now works end-to-end against the local model
(`nomic-embed-text:latest`), verified with real vectors back. `chat_json()`
against `gpt-oss:120b-cloud` through this local Ollama does **not**
reliably honor the `"strict": true` JSON-schema constraint on
`response_format` — one observed response was a bare JSON array
(`[{...}, {...}]`) instead of the required `{"topics": [...]}` object.
`LLMClient` correctly rejected it (`LLMError`, no silent guessing) — that
is the guardrail working as designed, not a bug to paper over. Whether
real Ollama Cloud (with a genuine API key) enforces the schema more
strictly than this local/proxied setup is untested; see `TODO.md` Phase 2
follow-ups.

### Follow-up: live-model smoke test

Added `backend/tests/live/test_llm_client_live.py` — real round-trips
through `LLMClient.embed()` and `topic_extractor.extract_topics()`
against whatever endpoint `.env` points at, marked `live_model` and
excluded from the default `uv run pytest` run (`addopts` in
`pyproject.toml`). Opt in with `RUN_LIVE_LLM_TESTS=1 uv run pytest -m
live_model` once a real endpoint is reachable — see
[runbook.md](../runbook.md#tests). The other two follow-ups (whether real
Ollama Cloud enforces `strict` JSON-schema output, and what to do if it
doesn't) still need a genuine `OLLAMA_API_KEY` to resolve and remain open
in `TODO.md`.
