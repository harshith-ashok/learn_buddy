import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.schemas import WorkedAnswerGradeContent
from src.core.config import get_settings
from src.core.llm_client import get_llm_client
from src.core.security import create_access_token, hash_password
from src.db.models import Document, DocumentStatus, Student, StudyKit, StudyKitType, Topic
from src.main import app

_PROBLEM_GUIDE_CONTENT = {
    "problems": [
        {
            "prompt": "A car accelerates from 0 to 20 m/s in 4 seconds. Find its acceleration.",
            "steps": [
                {"text": "a = change in velocity / time", "source_chunk_ids": []},
                {"text": "a = 20 / 4 = 5 m/s^2", "source_chunk_ids": []},
            ],
        }
    ],
    "formulas": [],
}


def _override_dependencies(fake_llm_client) -> None:
    app.dependency_overrides[get_llm_client] = lambda: fake_llm_client


async def _make_student_with_kit(db_session: AsyncSession, email: str) -> tuple[Student, str, StudyKit]:
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
    topic = Topic(document_id=document.id, name="Kinematics", description="", position=0)
    db_session.add(topic)
    await db_session.flush()
    kit = StudyKit(
        student_id=student.id,
        topic_id=topic.id,
        kit_type=StudyKitType.PROBLEM_GUIDE,
        content=_PROBLEM_GUIDE_CONTENT,
        source_chunk_ids=[],
    )
    db_session.add(kit)
    await db_session.flush()
    return student, create_access_token(str(student.id)), kit


async def test_grade_updates_mastery_and_history_shows_the_attempt(
    client: AsyncClient, db_session: AsyncSession, fake_agent_llm
) -> None:
    student, token, kit = await _make_student_with_kit(db_session, "wa1@example.com")
    fake_agent_llm.chat_responses[WorkedAnswerGradeContent] = WorkedAnswerGradeContent(
        gradable=True, is_correct=True, accuracy_score=1.0, overall_feedback="Nice work.", step_feedback=[]
    )
    _override_dependencies(fake_agent_llm)
    headers = {"Authorization": f"Bearer {token}"}
    body = {"study_kit_id": str(kit.id), "problem_index": 0, "work": "a = 20/4 = 5 m/s^2"}

    response = await client.post("/worked-answer/grade", headers=headers, json=body)
    history = await client.get(
        "/worked-answer", params={"study_kit_id": str(kit.id), "problem_index": 0}, headers=headers
    )

    assert response.status_code == 200
    resp_body = response.json()
    assert resp_body["covered"] is True
    assert resp_body["is_correct"] is True
    assert resp_body["new_mastery_score"] == 0.4  # 0*0.6 + 1.0*0.4

    assert history.status_code == 200
    assert len(history.json()) == 1
    assert history.json()[0]["work"] == "a = 20/4 = 5 m/s^2"


async def test_grade_rejects_a_bad_problem_index(
    client: AsyncClient, db_session: AsyncSession, fake_agent_llm
) -> None:
    student, token, kit = await _make_student_with_kit(db_session, "wa2@example.com")
    _override_dependencies(fake_agent_llm)

    response = await client.post(
        "/worked-answer/grade",
        headers={"Authorization": f"Bearer {token}"},
        json={"study_kit_id": str(kit.id), "problem_index": 9, "work": "some work"},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_problem_index"


async def test_grade_for_a_foreign_study_kit_is_not_found(
    client: AsyncClient, db_session: AsyncSession, fake_agent_llm
) -> None:
    _student, token, _kit = await _make_student_with_kit(db_session, "wa3@example.com")
    _override_dependencies(fake_agent_llm)

    response = await client.post(
        "/worked-answer/grade",
        headers={"Authorization": f"Bearer {token}"},
        json={"study_kit_id": str(uuid.uuid4()), "problem_index": 0, "work": "some work"},
    )

    assert response.status_code == 404


async def test_grade_is_rate_limited(client: AsyncClient, db_session: AsyncSession, fake_agent_llm) -> None:
    student, token, kit = await _make_student_with_kit(db_session, "wa4@example.com")
    fake_agent_llm.chat_responses[WorkedAnswerGradeContent] = WorkedAnswerGradeContent(gradable=False)
    _override_dependencies(fake_agent_llm)

    limit = get_settings().worked_answer_grade_rate_limit
    headers = {"Authorization": f"Bearer {token}"}
    body = {"study_kit_id": str(kit.id), "problem_index": 0, "work": "some work"}

    responses = [
        await client.post("/worked-answer/grade", headers=headers, json=body) for _ in range(limit + 1)
    ]

    assert [r.status_code for r in responses[:limit]] == [200] * limit
    assert responses[-1].status_code == 429
