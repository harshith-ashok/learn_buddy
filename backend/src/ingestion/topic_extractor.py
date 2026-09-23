import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.llm_client import LLMClient
from src.core.logging import get_logger
from src.db.models import Subtopic, Topic, TopicPrerequisite
from src.ingestion.schemas import ParsedDocument, TopicExtractionResult

logger = get_logger(__name__)

_MAX_OUTLINE_CHARS = 8000

_SYSTEM_PROMPT = (
    "You are a curriculum analyst. Given a syllabus or course material outline, "
    "extract the distinct topics it teaches. For each topic, give a short name, "
    "a one-to-two sentence description, a list of its subtopics, and a list of "
    "other topic names (from the same output) that must be learned first as "
    "prerequisites. Only reference topic names you are also emitting. Do not "
    "invent topics not supported by the provided text."
)


def _document_outline(document: ParsedDocument, max_chars: int = _MAX_OUTLINE_CHARS) -> str:
    """Flatten the heading tree into a bounded outline for the prompt.

    Full chunk text isn't needed here — headings plus a text excerpt per
    section are enough signal for topic extraction, and keeping this
    bounded caps prompt size regardless of document length.
    """
    lines: list[str] = []
    if document.title:
        lines.append(f"# {document.title}")

    def walk(sections, depth: int) -> None:
        for section in sections:
            if section.heading:
                lines.append(f"{'#' * min(depth + 1, 6)} {section.heading}")
            excerpt = section.text.strip().replace("\n", " ")
            if excerpt:
                lines.append(excerpt[:500])
            walk(section.children, depth + 1)

    walk(document.sections, 1)

    outline = "\n".join(lines)
    return outline[:max_chars]


async def extract_topics(
    document: ParsedDocument, llm_client: LLMClient, model: str | None = None
) -> TopicExtractionResult:
    """Call the classification model for a structured topic tree.

    Raises `LLMError` (via `llm_client.chat_json`) if the model's output
    doesn't validate against `TopicExtractionResult` — never falls back to
    a best-effort free-text parse.
    """
    outline = _document_outline(document)
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": outline},
    ]
    return await llm_client.chat_json(messages, TopicExtractionResult, model)


async def persist_topics(
    db: AsyncSession, document_id: uuid.UUID, extraction: TopicExtractionResult
) -> list[Topic]:
    """Write an extraction result as `topics` / `subtopics` / `topic_prerequisites` rows.

    Assumes the caller has already cleared any prior topics for this
    document (see `ingestion.pipeline` for the idempotent-reupload path).
    """
    topics_by_name: dict[str, Topic] = {}

    for position, extracted in enumerate(extraction.topics):
        topic = Topic(
            document_id=document_id,
            name=extracted.name,
            description=extracted.description,
            position=position,
        )
        db.add(topic)
        topics_by_name[extracted.name] = topic

    await db.flush()  # assign topic ids before creating subtopics/edges that reference them

    for extracted in extraction.topics:
        topic = topics_by_name[extracted.name]
        for sub_position, subtopic_name in enumerate(extracted.subtopics):
            db.add(
                Subtopic(
                    topic_id=topic.id,
                    name=subtopic_name,
                    description="",
                    position=sub_position,
                )
            )

        for prerequisite_name in extracted.prerequisites:
            prerequisite = topics_by_name.get(prerequisite_name)
            if prerequisite is None:
                logger.warning(
                    "Dropping prerequisite referencing an unknown topic",
                    extra={"topic": extracted.name, "prerequisite": prerequisite_name},
                )
                continue
            if prerequisite.name == extracted.name:
                logger.warning("Dropping self-referential prerequisite", extra={"topic": extracted.name})
                continue
            db.add(TopicPrerequisite(topic_id=topic.id, prerequisite_topic_id=prerequisite.id))

    await db.flush()
    return list(topics_by_name.values())
