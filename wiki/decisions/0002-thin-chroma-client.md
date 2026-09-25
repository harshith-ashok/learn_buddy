# ADR 0002: Use `chromadb-client==0.5.20`, not `chromadb`

## Problem

`core/vectorstore.py` needs a Chroma client to talk to the `chromadb`
service (Phase 0) over HTTP. The obvious choice, `pip install chromadb`,
is the same package the server itself is built from.

## Options considered

1. `chromadb` (full package) — includes the server, embedding functions,
   and `onnxruntime` for local embedding, even though this project only
   ever calls a remote `chromadb` server and gets embeddings from Ollama
   Cloud.
2. `chromadb-client` (thin package) — `HttpClient`-only, no server code,
   no bundled embedding functions.

## Choice

`chromadb-client`, version-pinned to `0.5.20` to match the
`chromadb/chroma:0.5.20` server image from `docker-compose.yml`.

Two problems ruled out option 1 directly: `chromadb`'s `onnxruntime`
dependency has no Python 3.10 wheel (this project targets 3.10 per
`backend/.python-version`), so `uv add chromadb` fails outright on this
stack. And even ignoring that, dragging in a local embedding/server
runtime for a process that only ever makes HTTP calls to a separate
container is the wrong shape for `core/vectorstore.py`'s job.

The version pin (rather than latest `chromadb-client`) matters
independently: Chroma has broken wire compatibility across major/minor
versions before, and the newest `chromadb-client` (1.5.x at the time of
writing) is several versions ahead of the pinned 0.5.20 server. Pinning
the client to the exact server version avoids finding out about a
protocol mismatch at runtime.

## Consequences

- `backend/pyproject.toml` pins `chromadb-client==0.5.20` rather than a
  `>=` range; bumping the `chromadb/chroma` image tag in
  `docker-compose.yml` should bump this pin in the same change.
- No local embedding capability exists in the backend process — by
  design; embeddings come from `OLLAMA_EMBED_MODEL` via Ollama Cloud
  (`CLAUDE.md` → "Model configuration"), not from Chroma's bundled
  functions.
