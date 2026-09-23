import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import create_access_token, hash_password
from src.db.models import Document, DocumentStatus, MasteryScore, Student, Topic, TopicPrerequisite


async def _make_authenticated_student(db_session: AsyncSession, email: str) -> tuple[Student, str]:
    student = Student(email=email, hashed_password=hash_password("x"), full_name="G")
    db_session.add(student)
    await db_session.flush()
    return student, create_access_token(str(student.id))


async def test_course_graph_includes_subtopics_prerequisites_and_mastery(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    student, token = await _make_authenticated_student(db_session, "graph1@example.com")
    document = Document(
        student_id=student.id,
        filename="notes.pdf",
        storage_path="/tmp/notes.pdf",
        content_hash=uuid.uuid4().hex,
        status=DocumentStatus.DONE,
    )
    db_session.add(document)
    await db_session.flush()

    prereq = Topic(document_id=document.id, name="Variables", description="", position=0)
    advanced = Topic(document_id=document.id, name="Loops", description="", position=1)
    db_session.add_all([prereq, advanced])
    await db_session.flush()

    db_session.add(TopicPrerequisite(topic_id=advanced.id, prerequisite_topic_id=prereq.id))
    db_session.add(MasteryScore(student_id=student.id, topic_id=prereq.id, score=0.5))
    await db_session.flush()

    response = await client.get(f"/graph/{document.id}", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["course_id"] == str(document.id)
    nodes_by_name = {node["name"]: node for node in body["topics"]}
    assert nodes_by_name["Variables"]["mastery_score"] == 0.5
    assert nodes_by_name["Loops"]["prerequisite_ids"] == [str(prereq.id)]


async def test_course_graph_for_foreign_document_is_not_found(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _owner, _ = await _make_authenticated_student(db_session, "graph-owner@example.com")
    _other, other_token = await _make_authenticated_student(db_session, "graph-other@example.com")

    response = await client.get(f"/graph/{uuid.uuid4()}", headers={"Authorization": f"Bearer {other_token}"})

    assert response.status_code == 404
