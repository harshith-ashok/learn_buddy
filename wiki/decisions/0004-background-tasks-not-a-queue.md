# ADR 0004: FastAPI `BackgroundTasks` for ingestion, not a dedicated task queue

## Problem

`TODO.md` says the upload endpoint "enqueues processing." Redis is already
in the stack, which is the obvious backing store for a real task queue
(Celery, RQ, arq).

## Options considered

1. **FastAPI `BackgroundTasks`.** Runs the ingestion pipeline as an
   in-process asyncio task after the response is sent, inside the
   `backend` container itself.
2. **A dedicated queue** (Celery/RQ/arq backed by Redis), with a separate
   worker process/container consuming jobs.

## Choice

`BackgroundTasks` (option 1), in `api/documents.py`.

A real queue is the right call once ingestion needs independent scaling
from the API process, retries across process restarts, or a worker fleet
— none of which apply yet: `docker-compose.yml` runs one `backend`
container, and Phase 0/1 didn't stand up a worker service or job-result
storage. Adding Celery now would mean a new container, a new queue
consumer, and new "is the worker alive" health-checking for no present
benefit. `BackgroundTasks` gets the one property that actually matters
today — the upload request returns immediately, before parsing/embedding
happens — with zero new infrastructure.

## Consequences

- Ingestion work dies with the `backend` process. A container restart
  mid-ingestion leaves a `document` stuck in `PROCESSING` with no retry;
  nothing currently detects or recovers that (a re-upload of the same
  file is the only recovery path right now).
- Ingestion competes with request handling for the same process's event
  loop — fine at current scale, a real constraint once upload volume or
  document size grows.
- The seam is already in place if this needs to change: `api/documents.py`
  depends on `LLMClientDep`/`VectorStoreDep`/`SessionFactoryDep` and calls
  `ingestion.pipeline.process_document(...)` with plain arguments — moving
  that call into a Celery task body (or an RQ job) instead of
  `background_tasks.add_task(...)` is a small, localized change, not a
  rewrite of the pipeline itself.
