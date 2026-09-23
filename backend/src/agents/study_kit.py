import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.retrieval import retrieve_context
from src.agents.schemas import (
    FlashcardsContent,
    NotCovered,
    ProblemGuideContent,
    QuizContent,
    StudyKitResult,
    SummaryContent,
)
from src.core.config import Settings, get_settings
from src.core.llm_client import LLMClient
from src.core.logging import get_logger
from src.core.vectorstore import VectorStoreClient
from src.db.models import StudyKit, StudyKitType
from src.domain import topics as topics_domain

logger = get_logger(__name__)

# Public: `api.study_kit` reuses this to re-validate a stored row's raw JSON
# on the way out, so a field added to a schema after a kit was generated
# (e.g. `formulas`) backfills its default for old rows instead of the
# frontend reading `undefined` for a field its types say always exists.
CONTENT_SCHEMA_BY_KIT_TYPE = {
    StudyKitType.SUMMARY: SummaryContent,
    StudyKitType.FLASHCARDS: FlashcardsContent,
    StudyKitType.QUIZ: QuizContent,
    StudyKitType.PROBLEM_GUIDE: ProblemGuideContent,
}

_SYSTEM_PROMPT = (
    "You are a study assistant. Using ONLY the numbered source excerpts below, produce "
    "{kit_type} material for the topic '{topic_name}'. Every fact must be grounded in one "
    "of the excerpts — set source_chunk_ids to the ids of the excerpts it came from. Do not "
    "introduce facts the excerpts don't support. If your response schema has a `formulas` "
    "field and the excerpts contain mathematical or scientific formulas central to this "
    "topic, list each as bare LaTeX (no $ or \\[ delimiters) with a short label and "
    "description; leave `formulas` empty if none of the excerpts contain one — never invent "
    "a formula the excerpts don't state."
)


def _context_block(chunks: list) -> str:
    return "\n\n".join(f"[{chunk.chunk_id}] {chunk.text}" for chunk in chunks)


async def generate_study_kit(
    db: AsyncSession,
    student_id: uuid.UUID,
    topic_id: uuid.UUID,
    kit_type: StudyKitType,
    llm_client: LLMClient,
    vectorstore: VectorStoreClient,
    settings: Settings | None = None,
) -> StudyKitResult | NotCovered:
    """Generate a `kit_type` study kit for `topic_id`, grounded in the student's own material.

    Retrieves context first; if nothing clears the similarity threshold,
    returns `NotCovered` without calling the model — the guardrail from
    `CLAUDE.md` → "Agent classification"'s sibling rule for retrieval.
    """
    settings = settings or get_settings()
    topic = await topics_domain.get_for_student(db, student_id, topic_id)

    query = f"{topic.name}. {topic.description or ''}".strip()
    retrieval = await retrieve_context(query, student_id, topic, llm_client, vectorstore, settings)
    if not retrieval.covered:
        logger.info(
            "Study kit request not covered by materials",
            extra={"student_id": str(student_id), "topic_id": str(topic_id), "kit_type": kit_type.value},
        )
        return NotCovered()

    schema = CONTENT_SCHEMA_BY_KIT_TYPE[kit_type]
    messages = [
        {
            "role": "system",
            "content": _SYSTEM_PROMPT.format(
                kit_type=kit_type.value.replace("_", " "), topic_name=topic.name
            ),
        },
        {"role": "user", "content": _context_block(retrieval.chunks)},
    ]
    content = await llm_client.chat_json(messages, schema)

    logger.info(
        "Generated study kit",
        extra={"student_id": str(student_id), "topic_id": str(topic_id), "kit_type": kit_type.value},
    )
    return StudyKitResult(
        kit_type=kit_type.value, content=content, source_chunk_ids=retrieval.source_chunk_ids
    )


async def persist_study_kit(
    db: AsyncSession, student_id: uuid.UUID, topic_id: uuid.UUID, result: StudyKitResult
) -> StudyKit:
    study_kit = StudyKit(
        student_id=student_id,
        topic_id=topic_id,
        kit_type=StudyKitType(result.kit_type),
        content=result.content.model_dump(mode="json"),
        source_chunk_ids=result.source_chunk_ids,
    )
    db.add(study_kit)
    await db.flush()
    return study_kit
