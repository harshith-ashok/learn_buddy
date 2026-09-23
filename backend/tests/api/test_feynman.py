import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.schemas import FeynmanGradeContent
from src.core.config import get_settings
from src.core.llm_client import get_llm_client
from src.core.security import create_access_token, hash_password
from src.core.vectorstore import get_vectorstore_client
from src.db.models import Document, DocumentStatus, Student, Topic
from src.main import app


def _override_dependencies(fake_llm_client, test_vectorstore) -> None:
    app.dependency_overrides[get_llm_client] = lambda: fake_llm_client
    app.dependency_overrides[get_vectorstore_client] = lambda: test_vectorstore


async def _make_student_with_topic(db_session: AsyncSession, email: str) -> tuple[Student, str, Topic]:
    student = Student(email=email, hashed_password=hash_password("x"), full_name="S")
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
    topic = Topic(document_id=document.id, name="Loops", description="For and while loops", position=0)
    db_session.add(topic)
    await db_session.flush()
    return student, create_access_token(str(student.id)), topic


async def test_grade_not_covered_returns_null_mastery_fields(
    client: AsyncClient, db_session: AsyncSession, fake_agent_llm, test_vectorstore
) -> None:
    student, token, topic = await _make_student_with_topic(db_session, "feyn1@example.com")
    _override_dependencies(fake_agent_llm, test_vectorstore)

    response = await client.post(
        "/feynman/grade",
        headers={"Authorization": f"Bearer {token}"},
        json={"topic_id": str(topic.id), "explanation": "A for loop repeats things."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["covered"] is False
    assert body["new_mastery_score"] is None


async def test_grade_updates_mastery_and_history_shows_the_attempt(
    client: AsyncClient, db_session: AsyncSession, fake_agent_llm, test_vectorstore
) -> None:
    student, token, topic = await _make_student_with_topic(db_session, "feyn2@example.com")
    query = f"{topic.name}. {topic.description}"
    fake_agent_llm.embeddings[query] = [1.0, 0.0]
    collection = test_vectorstore.get_or_create_collection(str(student.id))
    collection.add(
        ids=["doc:0"],
        embeddings=[[1.0, 0.0]],
        documents=["A for loop repeats a block a fixed number of times."],
        metadatas=[{"document_id": str(topic.document_id), "section_heading": "Loops"}],
    )
    fake_agent_llm.chat_responses[FeynmanGradeContent] = FeynmanGradeContent(
        gradable=True, accuracy_score=0.6, overall_feedback="Good start."
    )
    _override_dependencies(fake_agent_llm, test_vectorstore)
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post(
        "/feynman/grade",
        headers=headers,
        json={"topic_id": str(topic.id), "explanation": "A for loop repeats a block."},
    )
    history = await client.get("/feynman", params={"topic_id": str(topic.id)}, headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["covered"] is True
    assert body["accuracy_score"] == 0.6
    assert body["new_mastery_score"] == 0.24  # 0*0.6 + 0.6*0.4

    assert history.status_code == 200
    assert len(history.json()) == 1
    assert history.json()[0]["explanation"] == "A for loop repeats a block."


async def test_grade_is_rate_limited(
    client: AsyncClient, db_session: AsyncSession, fake_agent_llm, test_vectorstore
) -> None:
    student, token, topic = await _make_student_with_topic(db_session, "feyn3@example.com")
    _override_dependencies(fake_agent_llm, test_vectorstore)

    limit = get_settings().feynman_grade_rate_limit
    headers = {"Authorization": f"Bearer {token}"}
    body = {"topic_id": str(topic.id), "explanation": "A for loop repeats things."}

    responses = [await client.post("/feynman/grade", headers=headers, json=body) for _ in range(limit + 1)]

    assert [r.status_code for r in responses[:limit]] == [200] * limit
    assert responses[-1].status_code == 429
    assert responses[-1].json()["code"] == "rate_limited"


async def test_grade_rejects_an_empty_explanation(
    client: AsyncClient, db_session: AsyncSession, fake_agent_llm, test_vectorstore
) -> None:
    student, token, topic = await _make_student_with_topic(db_session, "feyn4@example.com")
    _override_dependencies(fake_agent_llm, test_vectorstore)

    response = await client.post(
        "/feynman/grade",
        headers={"Authorization": f"Bearer {token}"},
        json={"topic_id": str(topic.id), "explanation": ""},
    )

    assert response.status_code == 422
