import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.schemas import ChatAnswerContent
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


async def test_ask_not_covered_still_returns_200_with_a_refusal(
    client: AsyncClient, db_session: AsyncSession, fake_agent_llm, test_vectorstore
) -> None:
    student, token, topic = await _make_student_with_topic(db_session, "chat1@example.com")
    _override_dependencies(fake_agent_llm, test_vectorstore)

    response = await client.post(
        "/chat/ask",
        headers={"Authorization": f"Bearer {token}"},
        json={"topic_id": str(topic.id), "message": "what is a for loop?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "assistant"
    assert body["covered"] is False
    assert "only answer questions about this topic" in body["content"].lower()


async def test_ask_persists_both_turns_and_returns_the_assistant_message(
    client: AsyncClient, db_session: AsyncSession, fake_agent_llm, test_vectorstore
) -> None:
    student, token, topic = await _make_student_with_topic(db_session, "chat2@example.com")
    query = "what is a for loop?"
    fake_agent_llm.embeddings[query] = [1.0, 0.0]
    collection = test_vectorstore.get_or_create_collection(str(student.id))
    collection.add(
        ids=["doc:0"],
        embeddings=[[1.0, 0.0]],
        documents=["A for loop repeats a block a fixed number of times."],
        metadatas=[{"document_id": str(topic.document_id), "section_heading": "Loops"}],
    )
    fake_agent_llm.chat_responses[ChatAnswerContent] = ChatAnswerContent(
        answerable=True, answer="A for loop repeats a block.", source_chunk_ids=["doc:0"]
    )
    _override_dependencies(fake_agent_llm, test_vectorstore)
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post(
        "/chat/ask", headers=headers, json={"topic_id": str(topic.id), "message": query}
    )
    history = await client.get("/chat", params={"topic_id": str(topic.id)}, headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["covered"] is True
    assert body["content"] == "A for loop repeats a block."
    assert body["source_chunk_ids"] == ["doc:0"]

    assert history.status_code == 200
    transcript = history.json()
    assert [(message["role"], message["content"]) for message in transcript] == [
        ("user", query),
        ("assistant", "A for loop repeats a block."),
    ]


async def test_chat_is_scoped_to_the_topics_own_document(
    client: AsyncClient, db_session: AsyncSession, fake_agent_llm, test_vectorstore
) -> None:
    """A chunk belonging to some other document must never ground a topic-chat answer."""
    student, token, topic = await _make_student_with_topic(db_session, "chat3@example.com")
    query = "what is a for loop?"
    fake_agent_llm.embeddings[query] = [1.0, 0.0]
    collection = test_vectorstore.get_or_create_collection(str(student.id))
    collection.add(
        ids=["doc:0"],
        embeddings=[[1.0, 0.0]],
        documents=["A for loop repeats a block a fixed number of times."],
        metadatas=[{"document_id": str(uuid.uuid4()), "section_heading": "Loops"}],  # a different document
    )
    _override_dependencies(fake_agent_llm, test_vectorstore)

    response = await client.post(
        "/chat/ask",
        headers={"Authorization": f"Bearer {token}"},
        json={"topic_id": str(topic.id), "message": query},
    )

    assert response.status_code == 200
    assert response.json()["covered"] is False
    assert fake_agent_llm.chat_calls == []


async def test_ask_is_rate_limited(
    client: AsyncClient, db_session: AsyncSession, fake_agent_llm, test_vectorstore
) -> None:
    student, token, topic = await _make_student_with_topic(db_session, "chat4@example.com")
    _override_dependencies(fake_agent_llm, test_vectorstore)

    limit = get_settings().chat_ask_rate_limit
    headers = {"Authorization": f"Bearer {token}"}
    body = {"topic_id": str(topic.id), "message": "what is a for loop?"}

    responses = [await client.post("/chat/ask", headers=headers, json=body) for _ in range(limit + 1)]

    assert [r.status_code for r in responses[:limit]] == [200] * limit
    assert responses[-1].status_code == 429
    assert responses[-1].json()["code"] == "rate_limited"


async def test_ask_rejects_an_empty_message(
    client: AsyncClient, db_session: AsyncSession, fake_agent_llm, test_vectorstore
) -> None:
    student, token, topic = await _make_student_with_topic(db_session, "chat5@example.com")
    _override_dependencies(fake_agent_llm, test_vectorstore)

    response = await client.post(
        "/chat/ask",
        headers={"Authorization": f"Bearer {token}"},
        json={"topic_id": str(topic.id), "message": ""},
    )

    assert response.status_code == 422
