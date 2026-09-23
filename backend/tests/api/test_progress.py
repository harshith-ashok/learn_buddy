import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import create_access_token, hash_password
from src.db.models import Document, DocumentStatus, MasteryScore, Student, Topic


async def _make_authenticated_student(db_session: AsyncSession, email: str) -> tuple[Student, str]:
    student = Student(email=email, hashed_password=hash_password("x"), full_name="P")
    db_session.add(student)
    await db_session.flush()
    return student, create_access_token(str(student.id))


async def test_progress_lists_topics_with_mastery(client: AsyncClient, db_session: AsyncSession) -> None:
    student, token = await _make_authenticated_student(db_session, "progress1@example.com")
    document = Document(
        student_id=student.id,
        filename="notes.pdf",
        storage_path="/tmp/notes.pdf",
        content_hash=uuid.uuid4().hex,
        status=DocumentStatus.DONE,
    )
    db_session.add(document)
    await db_session.flush()

    scored = Topic(document_id=document.id, name="Loops", description="", position=0)
    unscored = Topic(document_id=document.id, name="Recursion", description="", position=1)
    db_session.add_all([scored, unscored])
    await db_session.flush()
    db_session.add(MasteryScore(student_id=student.id, topic_id=scored.id, score=0.7, consecutive_failures=1))
    await db_session.flush()

    response = await client.get(f"/progress/{student.id}", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    by_name = {row["topic_name"]: row for row in body["topics"]}
    assert by_name["Loops"]["mastery_score"] == 0.7
    assert by_name["Loops"]["consecutive_failures"] == 1
    assert by_name["Recursion"]["mastery_score"] == 0.0


async def test_progress_for_another_student_is_forbidden(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _student_a, token_a = await _make_authenticated_student(db_session, "progress-a@example.com")
    student_b, _token_b = await _make_authenticated_student(db_session, "progress-b@example.com")

    response = await client.get(f"/progress/{student_b.id}", headers={"Authorization": f"Bearer {token_a}"})

    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"
