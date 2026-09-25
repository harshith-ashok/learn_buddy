# 0007: Quiz scoring is computed server-side, never trusted from the client

## Problem

`agents.schemas.QuizSubmission` (Phase 3) has a `score` field — the field
existed so `score_and_update_mastery` could be built and unit-tested
before there was an API layer to feed it. Phase 4's `POST /quiz/submit`
needed to decide: pass a client-supplied score straight through, or grade
the submission against the quiz's own stored answers first.

## Options considered

- **Trust the client's `score`.** Simplest, no new code — but a student
  could submit any float and inflate their own mastery score. The
  `quiz_attempts.answers` column already stores the raw answers, which
  only makes sense if something is meant to grade them.
- **Grade server-side against `study_kits.content`.** `POST /quiz/submit`
  requires `study_kit_id`, loads that kit (ownership-checked), and grades
  the submitted answers against its stored `correct_index` per question
  (`agents/quiz_grading.py: grade_quiz`) before ever calling
  `score_and_update_mastery`.

## Choice

Grade server-side. `api/quiz.py`'s request schema (`QuizSubmitRequest`)
has no `score` field at all — it's structurally impossible for a client
to supply one. `agents.schemas.QuizSubmission` (the internal type
`score_and_update_mastery` takes) is unchanged; the API layer always
constructs it with a freshly computed score.

## Consequences

- A quiz submission must reference a real, owned `study_kits` row of
  `kit_type=quiz` — `POST /quiz/submit` rejects anything else (`400`/`404`
  before grading, see `api-reference.md`).
- `grade_quiz` only understands the `QuizContent` shape
  (`agents.schemas`); a study kit whose `content` doesn't have
  `questions` raises rather than silently scoring `0`.
- Grading server-side only closes half the gap: `POST /study-kit/generate`
  originally returned the freshly generated quiz's `content` verbatim,
  `correct_index` included — building the Phase 5 quiz view surfaced that
  a client could just read the answer out of the generate response
  without ever needing to guess. Fixed in the same phase:
  `api/study_kit.py: _redact_quiz_answers` strips `correct_index` from
  every quiz `content` this API ever returns (`generate`, `list`, `get`);
  grading is unaffected since it reads `study_kits.content` from the
  database, never from a prior API response.
