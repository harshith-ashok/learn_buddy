# Phase 3 — Agentic Core & Classification

## Goal

Build the LangGraph agent that sits behind every student-facing action:
classify what the student wants with one constrained model call, then
route strictly on that validated intent to one of four nodes —
recommend the next topic, generate a grounded study kit, score a quiz
submission and update mastery, and trigger remediation on repeated
failure or a mastery drop. Retrieval (semantic search, with a
keyword/BM25 fallback and a topic-targeted re-rank) grounds every study
kit in the student's own ingested material, with an explicit
"not covered in your materials" guardrail rather than a generated guess
when nothing clears the similarity threshold. No node hits a live model
in the default test suite; one smoke test behind a separate marker
proves the real round trip, mirroring the approach adopted for Phase 2's
follow-up.

## What was built

- **`agents/schemas.py`** — every Pydantic type the graph passes around:
  `Intent`/`IntentClassification`, `RetrievedChunk`/`RetrievalResult`,
  `Recommendation`/`NoRecommendation`, one content schema per study-kit
  type (`SummaryContent`, `FlashcardsContent`, `QuizContent`,
  `ProblemGuideContent`) plus `StudyKitResult`/`NotCovered`,
  `QuizSubmission`/`MasteryUpdateResult`, and `RemediationPlan`.
- **`agents/classify.py`** — one constrained call, `LLMError` → `other`,
  never a retried guess.
- **`agents/retrieval.py`** — semantic search over a Chroma candidate
  pool, an in-process BM25 keyword fallback (no full-text search engine
  in the stack), a coverage guardrail on `max(semantic, keyword)` against
  a fixed cosine-similarity threshold, and a topic-targeted lexical
  re-rank. See [agent-design.md](../agent-design.md) and
  [decisions/0005](../decisions/0005-cosine-similarity-for-retrieval-guardrail.md).
- **`agents/recommend.py`**, **`agents/study_kit.py`**,
  **`agents/mastery.py`**, **`agents/remediation.py`** — the four action
  nodes, detailed in [agent-design.md](../agent-design.md).
- **`agents/graph.py`** — `build_agent_graph` compiles a LangGraph
  `StateGraph` bound to one request's DB session/LLM client/vector store;
  `run_agent` is the single entry point Phase 4's API layer will call.
  Routing is on `Intent` alone, via `add_conditional_edges` — no
  free-form agent decision anywhere in the graph.
- **`domain/topics.py`** — student-scoped topic lookup (`get_for_student`),
  pulled out as its own domain module since three different agent nodes
  needed the same ownership check.
- **Config**: `retrieval_*`, `mastery_*`, `quiz_pass_threshold`,
  `remediation_*`, `exam_urgency_window_days` added to `core/config.py`
  — see `agent-design.md` for what each one tunes.
- **Tests**: `tests/agents/` (25 tests) — one file per node plus
  retrieval and the full graph, all against `FakeAgentLLMClient`
  (`tests/agents/conftest.py`) and a real (isolated) Chroma collection,
  no live model calls. `tests/live/test_agents_live.py` adds a
  `live_model`-marked smoke test for classification and retrieval,
  opt-in via `RUN_LIVE_LLM_TESTS=1`, mirroring Phase 2's follow-up.

## Harder than expected

Threshold-based retrieval coverage needed a bounded, embedding-model-
independent similarity score to be meaningful at all — Chroma's default
L2 distance isn't one. Moving collections to cosine space
([decisions/0005](../decisions/0005-cosine-similarity-for-retrieval-guardrail.md))
was a small code change but is the kind of thing that's easy to get wrong
silently (a threshold that "works" in one embedding model's scale and
silently gates everything in another's).

`datetime` handling for exam-date urgency needed a second pass:
`Document.exam_date` is stored as a naive `TIMESTAMP` (no `timezone=True`
on that column, unlike the `TimestampMixin` columns), so
`_exam_urgency`'s `now` has to be naive UTC too — a timezone-aware `now`
fails at the database boundary (asyncpg won't compare aware and naive
datetimes), not at the point where the mismatch is introduced.

## Deviations from the plan

`TODO.md` doesn't specify how a recommendation's justification or a
remediation plan's message should be produced. Both are composed
deterministically from already-computed values instead of a model call —
see [decisions/0006](../decisions/0006-deterministic-justification-text.md).
