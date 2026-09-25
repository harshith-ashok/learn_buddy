# Data Model

Postgres schema, managed by Alembic (`backend/migrations/`). Every table
has a UUID primary key (`id`) and `created_at`/`updated_at` timestamps via
shared mixins (`src/db/models/mixins.py`); those columns are omitted below
for brevity.

```mermaid
erDiagram
  STUDENTS ||--o{ DOCUMENTS : uploads
  DOCUMENTS ||--o{ TOPICS : contains
  TOPICS ||--o{ SUBTOPICS : contains
  TOPICS ||--o{ TOPIC_PREREQUISITES : "is prerequisite of"
  STUDENTS ||--o{ MASTERY_SCORES : has
  TOPICS ||--o{ MASTERY_SCORES : "scored on"
  STUDENTS ||--o{ STUDY_KITS : generates
  TOPICS ||--o{ STUDY_KITS : "generated for"
  STUDENTS ||--o{ QUIZ_ATTEMPTS : submits
  TOPICS ||--o{ QUIZ_ATTEMPTS : "attempted on"
  STUDY_KITS ||--o{ QUIZ_ATTEMPTS : "graded from"
  STUDENTS ||--o{ CHAT_MESSAGES : sends
  TOPICS ||--o{ CHAT_MESSAGES : "asked about"
  STUDENTS ||--o{ FEYNMAN_ATTEMPTS : submits
  TOPICS ||--o{ FEYNMAN_ATTEMPTS : "explained"
  STUDENTS ||--o{ WORKED_ANSWER_ATTEMPTS : submits
  TOPICS ||--o{ WORKED_ANSWER_ATTEMPTS : "attempted on"
  STUDY_KITS ||--o{ WORKED_ANSWER_ATTEMPTS : "problem from"

  STUDENTS {
    string email UK
    string hashed_password
    string full_name
  }
  DOCUMENTS {
    uuid student_id FK
    string filename
    string storage_path
    string content_hash
    enum status
    datetime exam_date "nullable"
  }
  TOPICS {
    uuid document_id FK
    string name
    text description
    int position
  }
  SUBTOPICS {
    uuid topic_id FK
    string name
    text description
    int position
  }
  TOPIC_PREREQUISITES {
    uuid topic_id FK
    uuid prerequisite_topic_id FK
  }
  MASTERY_SCORES {
    uuid student_id FK
    uuid topic_id FK
    float score "0..1"
    int consecutive_failures
  }
  STUDY_KITS {
    uuid student_id FK
    uuid topic_id FK
    enum kit_type
    json content
    json source_chunk_ids
  }
  QUIZ_ATTEMPTS {
    uuid student_id FK
    uuid topic_id FK
    uuid study_kit_id FK "nullable"
    float score "0..1"
    json answers
  }
  CHAT_MESSAGES {
    uuid student_id FK
    uuid topic_id FK
    enum role "user | assistant"
    text content
    json source_chunk_ids
    json related_topic_ids
  }
  FEYNMAN_ATTEMPTS {
    uuid student_id FK
    uuid topic_id FK
    text explanation
    float accuracy_score "0..1"
    text overall_feedback
    json breakdown
    json missing_concepts
  }
  WORKED_ANSWER_ATTEMPTS {
    uuid student_id FK
    uuid topic_id FK
    uuid study_kit_id FK
    int problem_index
    text work
    bool is_correct
    float accuracy_score "0..1"
    text overall_feedback
    json step_feedback
    int first_error_step "nullable"
  }
```

## Tables

| Table | Purpose |
| --- | --- |
| `students` | Auth identity (`email` unique, bcrypt `hashed_password`) and display name. |
| `documents` | One uploaded syllabus/notes file. Doubles as the "course" concept: `exam_date` lives here (nullable) since a student can have more than one course, each with its own timeline. `content_hash` backs upload idempotency (Phase 2). `status` tracks ingestion progress. |
| `topics` | Top-level topic extracted from a document, ordered by `position`. |
| `subtopics` | Child of a topic, same shape as `topics` (`name`, `description`, `position`). |
| `topic_prerequisites` | Directed edge: `prerequisite_topic_id` must be learned before `topic_id`. Unique on the edge pair, checked to disallow self-loops. |
| `mastery_scores` | One row per `(student, topic)` — updated in place by `score_and_update_mastery` (Phase 3), not appended. `consecutive_failures` backs the remediation trigger. |
| `study_kits` | A generated study asset (`kit_type`: summary/flashcards/quiz/problem_guide). `content` is the kit's JSON payload; `source_chunk_ids` records the Chroma chunk ids it was grounded in, for citation. |
| `quiz_attempts` | One submitted quiz attempt, optionally linked to the `study_kits` row it was generated from (`SET NULL` on delete). |
| `chat_messages` | One turn (`user` or `assistant`) in a topic-scoped Q&A chat. An assistant turn's `source_chunk_ids` and `related_topic_ids` are both empty for a refusal — there's no separate "was this covered" column; the API derives it from whether either list is non-empty (see `api-reference.md` → Chat). |
| `feynman_attempts` | One Feynman-mode explanation attempt, graded claim-by-claim. `breakdown` is the graded claim list (JSON); `accuracy_score` also feeds `mastery_scores` at grading time via `apply_mastery_observation` — this row is the durable record of *why* mastery moved, not a second source of truth for the score. |
| `worked_answer_attempts` | One attempt at working out a specific problem. `study_kit_id` + `problem_index` locate the reference `Problem` inside that `problem_guide` kit's stored `content.problems` — there's no separate "problems" table. `step_feedback` is the graded per-step list (JSON); `first_error_step` is nullable (no error found). |

## Conventions

- All foreign keys `ON DELETE CASCADE`, except `quiz_attempts.study_kit_id`
  (`SET NULL` — losing the kit shouldn't delete attempt history).
- Constraint names follow a fixed naming convention
  (`src/db/base.py: NAMING_CONVENTION`) so Alembic autogenerate is
  deterministic across machines.
- `mastery_scores.score` and `quiz_attempts.score` are both checked to
  `[0, 1]` at the database level, not just in application code.
- Every query in `src/domain` and `src/api` must filter by the
  authenticated student's id — the schema does not enforce row-level
  security itself (see `runbook.md`, once it exists, for the current
  stance on this).

## Not modeled yet

Chroma chunk records (id, embedding, metadata, source document/topic) live
in the vector store, not Postgres — `src/core/vectorstore.py` owns that
connection. They're written starting in Phase 2.
