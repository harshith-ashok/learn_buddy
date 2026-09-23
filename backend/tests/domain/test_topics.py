import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.errors import NotFoundError
from src.core.security import hash_password
from src.db.models import Document, DocumentStatus, Student, Subtopic, Topic
from src.domain import topics as topics_domain


async def _make_student_with_document(db_session: AsyncSession) -> tuple[Student, Document]:
    student = Student(
        email=f"{uuid.uuid4().hex}@example.com", hashed_password=hash_password("x"), full_name="T"
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
    return student, document


async def test_get_for_student_raises_not_found_for_a_foreign_topic(db_session: AsyncSession) -> None:
    student, _document = await _make_student_with_document(db_session)
    with pytest.raises(NotFoundError):
        await topics_domain.get_for_student(db_session, student.id, uuid.uuid4())


async def test_get_course_graph_raises_not_found_for_a_foreign_document(db_session: AsyncSession) -> None:
    student, _document = await _make_student_with_document(db_session)
    with pytest.raises(NotFoundError):
        await topics_domain.get_course_graph(db_session, student.id, uuid.uuid4())


async def test_get_course_graph_returns_an_empty_list_when_the_document_has_no_topics(
    db_session: AsyncSession,
) -> None:
    student, document = await _make_student_with_document(db_session)

    nodes = await topics_domain.get_course_graph(db_session, student.id, document.id)

    assert nodes == []


async def test_get_course_graph_includes_subtopics(db_session: AsyncSession) -> None:
    student, document = await _make_student_with_document(db_session)
    topic = Topic(document_id=document.id, name="Loops", description="", position=0)
    db_session.add(topic)
    await db_session.flush()
    db_session.add(Subtopic(topic_id=topic.id, name="For loops", description="", position=0))
    db_session.add(Subtopic(topic_id=topic.id, name="While loops", description="", position=1))
    await db_session.flush()

    nodes = await topics_domain.get_course_graph(db_session, student.id, document.id)

    assert len(nodes) == 1
    assert [subtopic.name for subtopic in nodes[0].subtopics] == ["For loops", "While loops"]
