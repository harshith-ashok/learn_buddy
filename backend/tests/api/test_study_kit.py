import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.schemas import Flashcard, FlashcardsContent, QuizContent, QuizQuestion
from src.core.config import get_settings
from src.core.llm_client import get_llm_client
from src.core.security import create_access_token, hash_password
from src.core.vectorstore import get_vectorstore_client
from src.db.models import Document, DocumentStatus, Student, StudyKit, StudyKitType, Topic
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


async def test_generate_not_covered_returns_a_message_not_an_error(
    client: AsyncClient, db_session: AsyncSession, fake_agent_llm, test_vectorstore
) -> None:
    student, token, topic = await _make_student_with_topic(db_session, "kit1@example.com")
    _override_dependencies(fake_agent_llm, test_vectorstore)

    response = await client.post(
        "/study-kit/generate",
        headers={"Authorization": f"Bearer {token}"},
        json={"topic_id": str(topic.id), "kit_type": "flashcards"},
    )

    assert response.status_code == 201
    assert "isn't covered" in response.json()["message"].lower()


async def test_generate_persists_and_returns_the_study_kit(
    client: AsyncClient, db_session: AsyncSession, fake_agent_llm, test_vectorstore
) -> None:
    student, token, topic = await _make_student_with_topic(db_session, "kit2@example.com")
    query = f"{topic.name}. {topic.description}"
    fake_agent_llm.embeddings[query] = [1.0, 0.0]

    collection = test_vectorstore.get_or_create_collection(str(student.id))
    collection.add(
        ids=["doc:0"],
        embeddings=[[1.0, 0.0]],
        documents=["A for loop repeats a block a fixed number of times."],
        metadatas=[{"document_id": str(uuid.uuid4()), "section_heading": "Loops"}],
    )
    expected = FlashcardsContent(cards=[Flashcard(question="Q", answer="A", source_chunk_ids=["doc:0"])])
    fake_agent_llm.chat_responses[FlashcardsContent] = expected
    _override_dependencies(fake_agent_llm, test_vectorstore)

    response = await client.post(
        "/study-kit/generate",
        headers={"Authorization": f"Bearer {token}"},
        json={"topic_id": str(topic.id), "kit_type": "flashcards"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["kit_type"] == StudyKitType.FLASHCARDS.value
    assert body["content"]["cards"][0]["question"] == "Q"


async def test_generate_is_rate_limited(
    client: AsyncClient, db_session: AsyncSession, fake_agent_llm, test_vectorstore
) -> None:
    """The dependency's limit is fixed at router-construction time from `Settings`
    (production config doesn't change mid-run), so the test exercises the
    real configured limit rather than mutating it after the fact."""
    student, token, topic = await _make_student_with_topic(db_session, "kit3@example.com")
    _override_dependencies(fake_agent_llm, test_vectorstore)

    limit = get_settings().study_kit_generation_rate_limit
    headers = {"Authorization": f"Bearer {token}"}
    body = {"topic_id": str(topic.id), "kit_type": "flashcards"}

    responses = [
        await client.post("/study-kit/generate", headers=headers, json=body) for _ in range(limit + 1)
    ]

    assert [r.status_code for r in responses[:limit]] == [201] * limit
    assert responses[-1].status_code == 429
    assert responses[-1].json()["code"] == "rate_limited"


async def test_generate_redacts_correct_index_from_a_quiz_kit(
    client: AsyncClient, db_session: AsyncSession, fake_agent_llm, test_vectorstore
) -> None:
    student, token, topic = await _make_student_with_topic(db_session, "kit4@example.com")
    query = f"{topic.name}. {topic.description}"
    fake_agent_llm.embeddings[query] = [1.0, 0.0]
    collection = test_vectorstore.get_or_create_collection(str(student.id))
    collection.add(
        ids=["doc:0"],
        embeddings=[[1.0, 0.0]],
        documents=["A for loop repeats a block a fixed number of times."],
        metadatas=[{"document_id": str(uuid.uuid4()), "section_heading": "Loops"}],
    )
    fake_agent_llm.chat_responses[QuizContent] = QuizContent(
        questions=[
            QuizQuestion(question="Q", options=["a", "b"], correct_index=1, source_chunk_ids=["doc:0"])
        ]
    )
    _override_dependencies(fake_agent_llm, test_vectorstore)

    response = await client.post(
        "/study-kit/generate",
        headers={"Authorization": f"Bearer {token}"},
        json={"topic_id": str(topic.id), "kit_type": "quiz"},
    )

    assert response.status_code == 201
    question = response.json()["content"]["questions"][0]
    assert "correct_index" not in question
    assert question["options"] == ["a", "b"]


async def test_list_and_get_study_kits(
    client: AsyncClient, db_session: AsyncSession, fake_agent_llm, test_vectorstore
) -> None:
    student, token, topic = await _make_student_with_topic(db_session, "kit5@example.com")
    study_kit = StudyKit(
        student_id=student.id,
        topic_id=topic.id,
        kit_type=StudyKitType.SUMMARY,
        content={"points": [{"text": "x", "source_chunk_ids": []}]},
    )
    db_session.add(study_kit)
    await db_session.flush()
    headers = {"Authorization": f"Bearer {token}"}

    listed = await client.get("/study-kit", params={"topic_id": str(topic.id)}, headers=headers)
    fetched = await client.get(f"/study-kit/{study_kit.id}", headers=headers)

    assert listed.status_code == 200
    assert [kit["id"] for kit in listed.json()] == [str(study_kit.id)]
    assert fetched.status_code == 200
    assert fetched.json()["kit_type"] == StudyKitType.SUMMARY.value


async def test_a_row_predating_the_formulas_field_backfills_an_empty_list(
    client: AsyncClient, db_session: AsyncSession, fake_agent_llm, test_vectorstore
) -> None:
    """Regression test: a `study_kits` row written before `SummaryContent.formulas`
    existed has no `formulas` key in its stored JSON at all — the API must
    still return one (schema says it's always present), not `content.formulas`
    silently missing and crashing the frontend's `FormulaSheet`."""
    student, token, topic = await _make_student_with_topic(db_session, "kit6@example.com")
    study_kit = StudyKit(
        student_id=student.id,
        topic_id=topic.id,
        kit_type=StudyKitType.SUMMARY,
        content={"points": [{"text": "x", "source_chunk_ids": []}]},  # no "formulas" key
    )
    db_session.add(study_kit)
    await db_session.flush()

    fetched = await client.get(f"/study-kit/{study_kit.id}", headers={"Authorization": f"Bearer {token}"})

    assert fetched.status_code == 200
    assert fetched.json()["content"]["formulas"] == []
