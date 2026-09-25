# ADR 0014: Feynman-mode and worked-answer grading as first-class assessment types

## Problem

Two new features were requested: (1) "Feynman mode" — grade a student's
own explanation of a topic against the source material, pointing out
exactly where it breaks down, rather than only generating content for
them to read; (2) worked-answer grading — grade a student's own written
solution to a problem step-by-step, catching *where* reasoning went
wrong rather than only checking the final answer. Both are genuine
assessments, like a quiz, not generated study material — but neither
maps onto `study_kits` (which holds model-generated content the student
reads, not something a student submits) or `quiz_attempts` (schema is
multiple-choice-specific: `answers: [{question_index, selected_index}]`
scored against a stored `correct_index`).

## Options considered

1. Extend `quiz_attempts`/`QuizSubmission` to also hold free-text
   explanations and worked solutions, with nullable columns for the
   quiz-specific fields.
2. Two new tables/agent modules (`feynman_attempts` + `agents/feynman.py`,
   `worked_answer_attempts` + `agents/worked_answer.py`), each owning its
   own persistence, sharing only the mastery-update math with quiz
   grading.

## Choice

Option 2. A `quiz_attempts` row with `answers=null` and a paragraph of
free text in some repurposed column would violate this schema's own
convention (every table's columns describe one real Postgres-enforced
shape — see `data-model.md` → "Conventions") and would make `QuizView`'s
correct_index-stripping logic ambiguous for a type that never had a
`correct_index` to strip. Two focused tables are more columns overall
but every column means one specific thing.

The one piece of logic actually shared across all three assessment
types — the mastery EMA update and remediation-trigger check — was
extracted from `agents/mastery.py: score_and_update_mastery` into
`apply_mastery_observation(db, student_id, topic_id, observed_score,
settings) -> MasteryUpdateResult`, which takes a bare `float` score and
persists nothing itself. `score_and_update_mastery` (quiz) is now a thin
wrapper that calls it and adds `QuizAttempt` persistence;
`agents/feynman.py` and `agents/worked_answer.py` call the same shared
function and each add their own attempt-row persistence. This means a
real explanation or a real worked solution moves mastery exactly the
same way a quiz score does — "real understanding" is a mastery signal,
not a second parallel score living outside the system the rest of the
app (recommendations, remediation, the ledger's mastery ticks) already
reads from.

**Worked-answer grading skips retrieval entirely** — the one structural
difference from Feynman mode / chat. Its reference is a specific
`Problem` (prompt + steps) already stored verbatim in a `problem_guide`
study kit's `content` column; that problem was itself generated from the
topic's material when the kit was created, so re-running a Chroma
similarity search to re-derive grounding chunks would be redundant
network round-trips for context the database already has. "Coverage"
here means "does `study_kit_id` + `problem_index` resolve to a real
problem" (an existence/ownership check, `AppError` on failure) rather
than a similarity threshold — the model's own `gradable` self-guardrail
is still there for a non-attempt submission, same as everywhere else.

**LaTeX formulas** (the "separate section for formulas" part of the
same request) piggyback on the existing `SummaryContent`/`ProblemGuideContent`
schemas as an optional `formulas: list[Formula]` field (`label`, bare
LaTeX `latex`, `description`) rather than a new kit type — the system
prompt instructs the model to populate it only when the excerpts
actually contain formulas, empty otherwise (see `agents/study_kit.py`).
The frontend's `Latex` component renders via KaTeX and needs no `"use
client"` (`katex.renderToString` is pure string transformation, no DOM),
and falls back to showing the raw expression, visibly marked, if it
fails to parse — model-generated LaTeX isn't guaranteed valid, and a
parse failure shouldn't take the page down.

## Consequences

- `agents/mastery.py`'s public surface grew by one function
  (`apply_mastery_observation`); `score_and_update_mastery`'s signature
  and behavior are unchanged (verified by the existing quiz test suite
  passing unmodified against the refactor).
- Three attempt tables now record "why mastery moved" for a given topic
  (`quiz_attempts`, `feynman_attempts`, `worked_answer_attempts`) with no
  shared parent table — a future "full assessment history for this
  topic" view has to union three tables, not query one. Acceptable for
  now; revisit if a unified history view is actually requested.
- Neither Feynman-mode nor worked-answer grading are wired into
  `agents/graph.py`'s `Intent` enum/LangGraph — consistent with how
  `chat_ask` was added (see `agent-design.md`'s note on the graph vs.
  direct-call routes), not a gap specific to this change.
