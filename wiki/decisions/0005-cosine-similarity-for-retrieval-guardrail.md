# 0005: Cosine similarity for the retrieval coverage guardrail

## Problem

`agents.retrieval.retrieve_context` needs a "not covered in your
materials" guardrail: a fixed threshold below which it refuses to
generate. Chroma's default distance metric (`hnsw:space` unset) is
squared L2, which is unbounded and depends on embedding magnitude — there
is no fixed number that means "irrelevant" across different embedding
models or vector norms.

## Options considered

- **Keep default L2, threshold empirically.** No config change, but the
  threshold would need re-tuning per embedding model and isn't
  interpretable ("distance < 0.83" means nothing to a reviewer).
- **Cosine space, threshold on similarity in `[0, 1]`.** Requires setting
  `metadata={"hnsw:space": "cosine"}` on collection creation
  (`core/vectorstore.py`). A fixed threshold (`retrieval_similarity_threshold`)
  is portable across embedding models and legible in code review and
  logs.

## Choice

Cosine space. `VectorStoreClient.get_or_create_collection` now passes
`metadata={"hnsw:space": "cosine"}`. This changes Phase 2's collection
creation, but is safe: no real student data has been ingested yet against
a live Ollama Cloud endpoint (see `phases/phase-2-ingestion.md`'s
footnote), and test collections are ephemeral per test.

## Consequences

- `similarity = 1 - cosine_distance`, bounded `[0, 1]` (well, `[-1, 2]`
  before clamping — `retrieve_context` clamps to `[0, 1]`) — a threshold
  is a single, interpretable number.
- Any student data ingested before this change (there is none) would need
  re-embedding, since Chroma doesn't support changing a collection's
  space after creation.
