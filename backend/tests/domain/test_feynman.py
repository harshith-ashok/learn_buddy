import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import hash_password
from src.db.models import Document, DocumentStatus, FeynmanAttempt, Student, Topic
from src.domain import feynman as feynman_domain


async def _make_student_with_topic(db_session: AsyncSession) -> tuple[Student, Topic]:
    student = Student(
        email=f"{uuid.uuid4().hex}@example.com", hashed_password=hash_password("x"), full_name="F"
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


async def test_list_for_topic_returns_newest_first(db_session: AsyncSession) -> None:
    # Explicit, distinct `created_at`s: both rows are added within the same
    # test transaction, and Postgres's `now()` (the column's server_default)
    # is constant for a whole transaction, not per-statement — relying on
    # real elapsed time between the two flushes below would be flaky.
    now = datetime.now(timezone.utc)
    student, topic = await _make_student_with_topic(db_session)
    first = FeynmanAttempt(
        student_id=student.id,
        topic_id=topic.id,
        explanation="first try",
        accuracy_score=0.4,
        overall_feedback="",
        breakdown=[],
        missing_concepts=[],
        created_at=now,
    )
    db_session.add(first)
    await db_session.flush()
    second = FeynmanAttempt(
        student_id=student.id,
        topic_id=topic.id,
        explanation="second try",
        accuracy_score=0.8,
        overall_feedback="",
        breakdown=[],
        missing_concepts=[],
        created_at=now + timedelta(seconds=1),
    )
    db_session.add(second)
    await db_session.flush()

    attempts = await feynman_domain.list_for_topic(db_session, student.id, topic.id)

    assert [attempt.explanation for attempt in attempts] == ["second try", "first try"]


async def test_list_for_topic_is_scoped_to_the_student(db_session: AsyncSession) -> None:
    student, topic = await _make_student_with_topic(db_session)
    other_student, _other_topic = await _make_student_with_topic(db_session)
    db_session.add(
        FeynmanAttempt(
            student_id=student.id,
            topic_id=topic.id,
            explanation="mine",
            accuracy_score=0.5,
            overall_feedback="",
            breakdown=[],
            missing_concepts=[],
        )
    )
    await db_session.flush()

    attempts = await feynman_domain.list_for_topic(db_session, other_student.id, topic.id)

    assert attempts == []
