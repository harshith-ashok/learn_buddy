import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import hash_password
from src.db.models import (
    Document,
    DocumentStatus,
    Student,
    StudyKit,
    StudyKitType,
    Topic,
    WorkedAnswerAttempt,
)
from src.domain import worked_answer as worked_answer_domain


async def _make_kit(db_session: AsyncSession) -> tuple[Student, StudyKit]:
    student = Student(
        email=f"{uuid.uuid4().hex}@example.com", hashed_password=hash_password("x"), full_name="W"
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
    topic = Topic(document_id=document.id, name="Kinematics", description="", position=0)
    db_session.add(topic)
    await db_session.flush()
    kit = StudyKit(
        student_id=student.id,
        topic_id=topic.id,
        kit_type=StudyKitType.PROBLEM_GUIDE,
        content={"problems": [{"prompt": "p1", "steps": []}, {"prompt": "p2", "steps": []}]},
        source_chunk_ids=[],
    )
    db_session.add(kit)
    await db_session.flush()
    return student, kit


async def test_list_for_problem_returns_newest_first_and_filters_by_index(db_session: AsyncSession) -> None:
    # Explicit, distinct `created_at`s — see the equivalent comment in
    # tests/domain/test_feynman.py for why relying on real elapsed time
    # between flushes in the same transaction would be flaky.
    now = datetime.now(timezone.utc)
    student, kit = await _make_kit(db_session)
    for offset, (problem_index, work) in enumerate(
        [
            (0, "first attempt at p1"),
            (0, "second attempt at p1"),
            (1, "attempt at p2"),
        ]
    ):
        db_session.add(
            WorkedAnswerAttempt(
                student_id=student.id,
                topic_id=kit.topic_id,
                study_kit_id=kit.id,
                problem_index=problem_index,
                work=work,
                is_correct=False,
                accuracy_score=0.0,
                overall_feedback="",
                step_feedback=[],
                created_at=now + timedelta(seconds=offset),
            )
        )
        await db_session.flush()

    attempts = await worked_answer_domain.list_for_problem(db_session, student.id, kit.id, 0)

    assert [attempt.work for attempt in attempts] == ["second attempt at p1", "first attempt at p1"]


async def test_list_for_problem_is_scoped_to_the_student(db_session: AsyncSession) -> None:
    student, kit = await _make_kit(db_session)
    other_student, _other_kit = await _make_kit(db_session)
    db_session.add(
        WorkedAnswerAttempt(
            student_id=student.id,
            topic_id=kit.topic_id,
            study_kit_id=kit.id,
            problem_index=0,
            work="mine",
            is_correct=True,
            accuracy_score=1.0,
            overall_feedback="",
            step_feedback=[],
        )
    )
    await db_session.flush()

    attempts = await worked_answer_domain.list_for_problem(db_session, other_student.id, kit.id, 0)

    assert attempts == []
