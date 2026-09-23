import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import hash_password
from src.db.models import ChatMessageRole, Document, DocumentStatus, Student, Topic
from src.domain import chat as chat_domain


async def _make_student_with_topic(db_session: AsyncSession) -> tuple[Student, Topic]:
    student = Student(
        email=f"{uuid.uuid4().hex}@example.com", hashed_password=hash_password("x"), full_name="C"
    )
    db_session.add(student)
    await db_session.flush()
    document = Document(
        student_id=student.id,
        filename="notes.pdf",
        storage_path="/tmp/notes.pdf",
        content_hash=uuid.uuid4().hex,
        status=DocumentStatus.DONE,
    )
    db_session.add(document)
    await db_session.flush()
    topic = Topic(document_id=document.id, name="Loops", description="", position=0)
    db_session.add(topic)
    await db_session.flush()
    return student, topic


async def test_add_message_defaults_citations_to_empty(db_session: AsyncSession) -> None:
    student, topic = await _make_student_with_topic(db_session)

    message = await chat_domain.add_message(
        db_session, student.id, topic.id, ChatMessageRole.USER, "what is a for loop?"
    )

    assert message.role == ChatMessageRole.USER
    assert message.source_chunk_ids == []
    assert message.related_topic_ids == []


async def test_add_message_stores_citations_as_strings(db_session: AsyncSession) -> None:
    student, topic = await _make_student_with_topic(db_session)
    related_id = uuid.uuid4()

    message = await chat_domain.add_message(
        db_session,
        student.id,
        topic.id,
        ChatMessageRole.ASSISTANT,
        "A for loop repeats a block.",
        source_chunk_ids=["doc:0"],
        related_topic_ids=[related_id],
    )

    assert message.source_chunk_ids == ["doc:0"]
    assert message.related_topic_ids == [str(related_id)]


async def test_list_for_topic_returns_the_transcript_oldest_first(db_session: AsyncSession) -> None:
    student, topic = await _make_student_with_topic(db_session)
    await chat_domain.add_message(db_session, student.id, topic.id, ChatMessageRole.USER, "first")
    await chat_domain.add_message(db_session, student.id, topic.id, ChatMessageRole.ASSISTANT, "second")

    messages = await chat_domain.list_for_topic(db_session, student.id, topic.id)

    assert [message.content for message in messages] == ["first", "second"]


async def test_list_for_topic_is_scoped_to_the_student(db_session: AsyncSession) -> None:
    student, topic = await _make_student_with_topic(db_session)
    other_student, _other_topic = await _make_student_with_topic(db_session)
    await chat_domain.add_message(db_session, student.id, topic.id, ChatMessageRole.USER, "mine")

    messages = await chat_domain.list_for_topic(db_session, other_student.id, topic.id)

    assert messages == []
