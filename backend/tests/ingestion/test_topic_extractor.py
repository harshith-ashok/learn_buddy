from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import hash_password
from src.db.models import Document, DocumentStatus, Student, Subtopic, Topic, TopicPrerequisite
from src.ingestion.schemas import ExtractedTopic, TopicExtractionResult
from src.ingestion.topic_extractor import extract_topics, persist_topics


async def _make_document(db_session: AsyncSession) -> Document:
    student = Student(email="topics@example.com", hashed_password=hash_password("x"), full_name="T")
    db_session.add(student)
    await db_session.flush()

    document = Document(
        student_id=student.id,
        filename="syllabus.docx",
        storage_path="/tmp/syllabus.docx",
        content_hash="deadbeef",
        status=DocumentStatus.PENDING,
    )
    db_session.add(document)
    await db_session.flush()
    return document


async def test_extract_topics_delegates_to_chat_json(fake_llm_client) -> None:
    from src.ingestion.schemas import ParsedDocument

    fake_llm_client.extraction = TopicExtractionResult(
        topics=[ExtractedTopic(name="Loops", description="Iteration constructs")]
    )
    document = ParsedDocument(title="CS101", sections=[])

    result = await extract_topics(document, fake_llm_client)

    assert fake_llm_client.chat_calls == 1
    assert result.topics[0].name == "Loops"


async def test_persist_topics_writes_topics_subtopics_and_prerequisites(db_session: AsyncSession) -> None:
    document = await _make_document(db_session)
    extraction = TopicExtractionResult(
        topics=[
            ExtractedTopic(name="Variables", description="Storing values", subtopics=["Naming", "Scope"]),
            ExtractedTopic(
                name="Loops",
                description="Iteration",
                subtopics=["For loops", "While loops"],
                prerequisites=["Variables"],
            ),
        ]
    )

    topics = await persist_topics(db_session, document.id, extraction)
    await db_session.flush()

    assert {t.name for t in topics} == {"Variables", "Loops"}

    stored_topics = (await db_session.scalars(select(Topic).where(Topic.document_id == document.id))).all()
    assert len(stored_topics) == 2

    stored_subtopics = (
        await db_session.scalars(select(Subtopic).where(Subtopic.topic_id.in_([t.id for t in stored_topics])))
    ).all()
    assert {s.name for s in stored_subtopics} == {"Naming", "Scope", "For loops", "While loops"}

    edges = (await db_session.scalars(select(TopicPrerequisite))).all()
    assert len(edges) == 1
    loops = next(t for t in stored_topics if t.name == "Loops")
    variables = next(t for t in stored_topics if t.name == "Variables")
    assert edges[0].topic_id == loops.id
    assert edges[0].prerequisite_topic_id == variables.id


async def test_persist_topics_drops_dangling_and_self_referential_prerequisites(
    db_session: AsyncSession,
) -> None:
    document = await _make_document(db_session)
    extraction = TopicExtractionResult(
        topics=[
            ExtractedTopic(
                name="Recursion",
                description="Functions calling themselves",
                prerequisites=["Recursion", "Does Not Exist"],
            ),
        ]
    )

    await persist_topics(db_session, document.id, extraction)
    await db_session.flush()

    edges = (await db_session.scalars(select(TopicPrerequisite))).all()
    assert edges == []
