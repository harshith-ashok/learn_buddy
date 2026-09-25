# ADR 0010: Use `json_object` + inline schema instruction, not `json_schema` strict mode

## Problem

Every document upload was ending in `documents.status = FAILED`. Tracing
it: ingestion reached `topic_extractor.extract_topics`, which calls
`LLMClient.chat_json` with `response_format: {type: json_schema, strict:
true}` per `CLAUDE.md` → "Structured output ... uses
JSON-schema-constrained responses". Against the deployed `gpt-oss:120b-cloud`
build served through this project's Ollama version, that mode is silently
ignored — the model returns markdown (a table or prose) instead of JSON,
so every `Pydantic` validation in `chat_json` failed with `Model output
did not match <Schema>`. Reproduced 3/3 times against a real uploaded
document's extraction prompt.

## Options considered

1. Keep `json_schema` strict mode and retry/backoff harder — doesn't
   help; failures were deterministic (bad output, not transient), not
   errors `_post_with_retry` treats as retryable.
2. Switch to `response_format: {type: json_object}` with no further
   change — reliably produced valid JSON, but as a bare array (e.g.
   `[{...}, ...]`) rather than the schema's required top-level object
   (`{"topics": [...]}`), so validation still failed.
3. `json_object` mode plus an explicit system message spelling out the
   target JSON Schema and demanding a single raw JSON object.

## Choice

Option 3, implemented once in `LLMClient.chat_json`
(`backend/src/core/llm_client.py`) so every caller (`topic_extractor`,
`agents/classify.py`, `agents/study_kit.py`) is fixed uniformly. The
method still validates the response against the caller's Pydantic schema
before returning — the deviation from `CLAUDE.md` is which `response_format`
mode requests the JSON, not the "never regex-parse free text, always
validate with Pydantic" guarantee, which is unchanged.

## Consequences

- If a future Ollama/model upgrade fixes `json_schema` strict-mode
  compliance, this can revert to the original `response_format` — re-run
  the reproduction (real document → `extract_topics`, 3 attempts) before
  reverting.
- The schema is now sent twice in spirit: once as a natural-language
  instruction (new) and implicitly via Pydantic validation (unchanged).
  Slightly larger prompt, no behavior change for callers.
