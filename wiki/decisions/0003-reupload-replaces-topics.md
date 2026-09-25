# ADR 0003: A re-upload fully replaces a document's topics, not merges them

## Problem

`TODO.md` requires re-uploading the same document (hash match) to "update
existing chunks/topics instead of duplicating them." Chunks are easy —
Chroma entries are deleted by `document_id` and rewritten. Topics are
harder: `mastery_scores`, `study_kits`, and `quiz_attempts` all reference
`topics.id`, `ON DELETE CASCADE`. So "replacing" a document's topics has a
real cost: a student's quiz history and generated study kits for that
document's old topics disappear with them.

## Options considered

1. **Full replace.** Delete all of a document's existing `topics` (cascade
   removes `subtopics`, `topic_prerequisites`, and anything referencing
   those topic ids) and persist the new extraction fresh.
2. **Identity-preserving merge.** Match new extracted topics to existing
   ones (by name, or by embedding similarity) and update in place, adding
   only genuinely new topics and leaving old ones alone so their mastery
   history survives.

## Choice

Full replace (option 1) — implemented in
`ingestion.pipeline._clear_existing_topics`.

Option 2 is the better experience but needs a real matching strategy
(exact name match breaks the moment the model phrases a topic slightly
differently between runs; embedding-similarity matching needs a threshold,
a tie-breaking rule, and its own tests) that's a project in itself and
isn't asked for by Phase 2's scope. Re-uploads are also expected to be
rare relative to first uploads — a student re-uploads because their
syllabus changed, not on a tight loop — so the cost of a full replace is
paid infrequently.

## Consequences

- Re-uploading a document a student has already taken quizzes against
  silently discards that history the moment ingestion completes. There is
  no warning to the student before this happens — that's a product gap,
  not just an engineering one, worth flagging before this ships to real
  users.
- If identity-preserving merge is ever wanted, it replaces
  `_clear_existing_topics` + `persist_topics`'s blind-insert with a diff
  against the existing `topics` for that `document_id`, matched by name as
  a first pass.
