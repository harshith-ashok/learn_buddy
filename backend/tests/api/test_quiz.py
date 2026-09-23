import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import create_access_token, hash_password
from src.db.models import (
    Document,
    DocumentStatus,
    MasteryScore,
    Student,
    StudyKit,
    StudyKitType,
    Topic,
)

_QUIZ_CONTENT = {
    "questions": [
        {"question": "2+2?", "options": ["3", "4"], "correct_index": 1, "source_chunk_ids": []},
        {"question": "3+3?", "options": ["5", "6"], "correct_index": 1, "source_chunk_ids": []},
    ]
}


async def _make_student_with_quiz(
    db_session: AsyncSession, email: str
) -> tuple[Student, str, Topic, StudyKit]:
    student = Student(email=email, hashed_password=hash_password("x"), full_name="Q")
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
    topic = Topic(document_id=document.id, name="Arithmetic", description="", position=0)
    db_session.add(topic)
    await db_session.flush()
    study_kit = StudyKit(
        student_id=student.id, topic_id=topic.id, kit_type=StudyKitType.QUIZ, content=_QUIZ_CONTENT
    )
    db_session.add(study_kit)
    await db_session.flush()
    return student, create_access_token(str(student.id)), topic, study_kit


async def test_submit_quiz_grades_server_side_and_updates_mastery(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    student, token, topic, study_kit = await _make_student_with_quiz(db_session, "quiz1@example.com")

    response = await client.post(
        "/quiz/submit",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "topic_id": str(topic.id),
            "study_kit_id": str(study_kit.id),
            "answers": [
                {"question_index": 0, "selected_index": 1},
                {"question_index": 1, "selected_index": 1},
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["score"] == 1.0
    assert body["is_pass"] is True
    assert body["remediation"] is None


async def test_submit_quiz_ignores_a_client_supplied_score(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """The request schema has no `score` field at all — grading is server-side, always."""
    student, token, topic, study_kit = await _make_student_with_quiz(db_session, "quiz2@example.com")

    response = await client.post(
        "/quiz/submit",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "topic_id": str(topic.id),
            "study_kit_id": str(study_kit.id),
            "answers": [
                {"question_index": 0, "selected_index": 0},  # wrong
                {"question_index": 1, "selected_index": 0},  # wrong
            ],
            "score": 1.0,  # ignored — not part of QuizSubmitRequest
        },
    )

    assert response.status_code == 200
    assert response.json()["score"] == 0.0


async def test_submit_quiz_triggers_remediation_on_two_failures(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    student, token, topic, study_kit = await _make_student_with_quiz(db_session, "quiz3@example.com")
    db_session.add(MasteryScore(student_id=student.id, topic_id=topic.id, score=0.5, consecutive_failures=1))
    await db_session.flush()

    response = await client.post(
        "/quiz/submit",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "topic_id": str(topic.id),
            "study_kit_id": str(study_kit.id),
            "answers": [
                {"question_index": 0, "selected_index": 0},
                {"question_index": 1, "selected_index": 0},
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["is_pass"] is False
    assert body["consecutive_failures"] == 2
    assert body["remediation"] is not None
    assert body["remediation"]["topic_id"] == str(topic.id)


async def test_submit_quiz_with_mismatched_topic_is_rejected(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    student, token, _topic, study_kit = await _make_student_with_quiz(db_session, "quiz4@example.com")

    response = await client.post(
        "/quiz/submit",
        headers={"Authorization": f"Bearer {token}"},
        json={"topic_id": str(uuid.uuid4()), "study_kit_id": str(study_kit.id), "answers": []},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_quiz_reference"


async def test_submit_quiz_for_a_foreign_study_kit_is_not_found(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _owner, _, topic, study_kit = await _make_student_with_quiz(db_session, "quiz-owner@example.com")
    other = Student(email="quiz-other@example.com", hashed_password=hash_password("x"), full_name="O")
    db_session.add(other)
    await db_session.flush()
    other_token = create_access_token(str(other.id))

    response = await client.post(
        "/quiz/submit",
        headers={"Authorization": f"Bearer {other_token}"},
        json={"topic_id": str(topic.id), "study_kit_id": str(study_kit.id), "answers": []},
    )

    assert response.status_code == 404
