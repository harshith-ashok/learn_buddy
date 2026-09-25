# API Reference

Every route lives behind `Bearer <access_token>` auth except `/health`
and `/auth/*`. Every error returns the `{code, message}` envelope
(`core/errors.py`); every data query is scoped to the authenticated
student — a path-level `student_id` is checked against the token's
subject, never trusted on its own.

## Auth

| Route | Auth | Body | Returns |
| --- | --- | --- | --- |
| `POST /auth/register` | none | `{email, password, full_name}` | `201` `{access_token, refresh_token, token_type}` |
| `POST /auth/login` | none | `{email, password}` | `200` token pair |
| `POST /auth/refresh` | none | `{refresh_token}` | `200` a **new** token pair; the presented refresh token is blacklisted on use (rotation) |
| `POST /auth/logout` | none | `{refresh_token}` | `204`; blacklists that refresh token early |

Access tokens: 15 min default (`ACCESS_TOKEN_EXPIRE_MINUTES`). Refresh
tokens: 7 days default (`REFRESH_TOKEN_EXPIRE_DAYS`), single-use —
rotation blacklists the `jti` in Redis for its remaining validity.
Logout doesn't revoke a still-live access token; see
`wiki/runbook.md` for the Phase 6 hardening note.

## Documents

| Route | Body / Params | Returns |
| --- | --- | --- |
| `POST /documents/upload` | multipart: `file`, optional `exam_date` | `200` `{id, filename, status, created}`; enqueues ingestion |
| `GET /documents` | — | `200` list of `{id, filename, status, exam_date}` |
| `GET /documents/{document_id}` | — | `200` same shape, `404` if not owned |

## Graph

| Route | Returns |
| --- | --- |
| `GET /graph/{course_id}` | `200` `{course_id, topics: [{id, name, description, position, mastery_score, subtopics, prerequisite_ids}]}`. `course_id` is a `documents.id` — a document doubles as a "course" (see `data-model.md`). `404` if not owned. |

## Progress

| Route | Returns |
| --- | --- |
| `GET /progress/{student_id}` | `200` `{student_id, topics: [{topic_id, topic_name, document_id, mastery_score, consecutive_failures}]}`. `403` if `student_id` isn't the caller's own. |

## Recommendation

| Route | Returns |
| --- | --- |
| `GET /recommendation/next` | `200` either `{topic_id, topic_name, mastery_score, justification}` or `{reason}` (no topic ready to recommend) — see `agent-design.md`. |

## Study kit

| Route | Body / Params | Returns |
| --- | --- | --- |
| `POST /study-kit/generate` | `{topic_id, kit_type}` (`kit_type`: `summary`\|`flashcards`\|`quiz`\|`problem_guide`) | `201` `{id, topic_id, kit_type, content, source_chunk_ids}`, or `{message}` if nothing in the student's material clears the retrieval guardrail. Rate-limited: `429` `{code: "rate_limited", ...}` past `STUDY_KIT_GENERATION_RATE_LIMIT` (default 10) requests per `STUDY_KIT_GENERATION_RATE_LIMIT_WINDOW_SECONDS` (default 3600) per student — the only route here that calls the model to generate new content. |
| `GET /study-kit?topic_id=` | query: `topic_id` | `200` list of the same shape, newest first |
| `GET /study-kit/{study_kit_id}` | — | `200` same shape, `404` if not owned |

A `quiz` kit's `content.questions[].correct_index` is stripped from every
response above — grading (`POST /quiz/submit`) reads it from the database
row directly, never from what a client was shown, so returning it would
just hand out the answers (see
[decisions/0007](decisions/0007-server-side-quiz-grading.md)).

A `summary` or `problem_guide` kit's `content.formulas` is a list of
`{label, latex, description}` — bare LaTeX (no `$`/`\[` delimiters,
rendered by the frontend via KaTeX), populated only when the topic's
material actually contains formulas worth isolating; an empty list is the
normal case for non-quantitative topics, not a bug.

## Chat

| Route | Body / Params | Returns |
| --- | --- | --- |
| `POST /chat/ask` | `{topic_id, message}` (`message`: 1–2000 chars) | `200` `{id, topic_id, role: "assistant", content, source_chunk_ids, related_topics: [{topic_id, topic_name}], covered}`. Persists both the student's message and this reply as `chat_messages` rows first. `covered=false` means the retrieval or model guardrail refused (see `agent-design.md` → "Topic chat") — `content` is then the fixed refusal text, not model output. Rate-limited: `429` past `CHAT_ASK_RATE_LIMIT` (default 30) requests per `CHAT_ASK_RATE_LIMIT_WINDOW_SECONDS` (default 3600) per student. |
| `GET /chat?topic_id=` | query: `topic_id` | `200` the full transcript for that topic, oldest first, same shape as above (`role` is `"user"` or `"assistant"`). |

Every answer is grounded **only** in the asking topic's own document —
retrieval is filtered by `document_id`, not the student's whole corpus
(unlike study-kit generation). `related_topics` names sibling topics in
the same document whose material overlaps the chunks the answer used; it
is never invented — see
[decisions/0012](decisions/0012-topic-chat-guardrails.md).

## Quiz

| Route | Body | Returns |
| --- | --- | --- |
| `POST /quiz/submit` | `{topic_id, study_kit_id, answers: [{question_index, selected_index}]}` | `200` `{score, is_pass, previous_mastery_score, new_mastery_score, consecutive_failures, remediation}`. `score` is computed server-side from the quiz's stored correct answers — the request has no `score` field, so a client can't self-report mastery (see [decisions/0007](decisions/0007-server-side-quiz-grading.md)). `remediation` is `null` unless 2 consecutive failures or a ≥20% mastery drop fired it. `400` if `study_kit_id` isn't a quiz for `topic_id`; `404` if not owned. |

## Feynman mode

| Route | Body / Params | Returns |
| --- | --- | --- |
| `POST /feynman/grade` | `{topic_id, explanation}` (`explanation`: 1–4000 chars) | `200` `{covered, accuracy_score, overall_feedback, breakdown: [{claim, verdict, feedback, source_chunk_ids}], missing_concepts, previous_mastery_score, new_mastery_score, consecutive_failures, remediation}`. `verdict` is `"correct"` \| `"incomplete"` \| `"incorrect"`. `covered=false` means the retrieval or model guardrail refused (see `agent-design.md` → "Feynman mode") — every mastery field is then `null`, nothing was graded. A graded (covered) attempt always updates mastery, exactly like a quiz score. Rate-limited: `429` past `FEYNMAN_GRADE_RATE_LIMIT` (default 20) per `FEYNMAN_GRADE_RATE_LIMIT_WINDOW_SECONDS` (default 3600). |
| `GET /feynman?topic_id=` | query: `topic_id` | `200` every past attempt for that topic, newest first, `{id, topic_id, explanation, accuracy_score, overall_feedback, breakdown, missing_concepts}`. |

## Worked-answer grading

| Route | Body / Params | Returns |
| --- | --- | --- |
| `POST /worked-answer/grade` | `{study_kit_id, problem_index, work}` (`problem_index`: 0-based into that kit's `content.problems`; `work`: 1–4000 chars, the student's own free-text steps) | `200` `{covered, is_correct, accuracy_score, overall_feedback, step_feedback: [{step_number, student_text, verdict, feedback}], first_error_step, previous_mastery_score, new_mastery_score, consecutive_failures, remediation}`. `verdict` is `"correct"` \| `"incorrect"` \| `"unclear"`; `first_error_step` is `null` if every step was correct. `400` `invalid_study_kit_reference` if `study_kit_id` isn't a `problem_guide` kit, `invalid_problem_index` if out of range; `404` if the kit isn't owned. Graded against that problem's own stored reference steps — no fresh retrieval call (see `agent-design.md` → "Worked-answer grading"). Rate-limited: `429` past `WORKED_ANSWER_GRADE_RATE_LIMIT` (default 20) per `WORKED_ANSWER_GRADE_RATE_LIMIT_WINDOW_SECONDS` (default 3600). |
| `GET /worked-answer?study_kit_id=&problem_index=` | query: `study_kit_id`, `problem_index` | `200` every past attempt at that specific problem, newest first, `{id, study_kit_id, problem_index, work, is_correct, accuracy_score, overall_feedback, step_feedback, first_error_step}`. |

Both Feynman-mode and worked-answer grading share the same mastery update
as quiz submission (`agents.mastery.apply_mastery_observation`) and the
same `remediation` trigger/shape — see
[decisions/0014](decisions/0014-feynman-and-worked-answer-grading.md).

## Testing this layer

Two kinds of test, both described in [runbook.md](runbook.md#tests):

- `tests/api/` — in-process (`ASGITransport`), fake LLM client, real
  Postgres/Chroma/Redis. Runs in the default `uv run pytest`.
- `tests/e2e/` — real HTTP against the actual running `backend`
  container (`docker compose --profile test run --rm backend-tests`),
  marked `e2e`, excluded by default. Covers what an in-process client
  can't: real Docker networking, real uvicorn, a missing env var inside
  the container.
