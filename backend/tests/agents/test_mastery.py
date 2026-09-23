import uuid

import pytest

from src.agents.mastery import score_and_update_mastery
from src.agents.schemas import QuizAnswer, QuizSubmission
from src.core.errors import NotFoundError


async def test_first_quiz_creates_mastery_score_via_ema(
    db_session, student, make_document, make_topic
) -> None:
    document = await make_document()
    topic = await make_topic(document, "Loops")
    submission = QuizSubmission(
        study_kit_id=None, answers=[QuizAnswer(question_index=0, selected_index=1)], score=0.8
    )

    result = await score_and_update_mastery(db_session, student.id, topic.id, submission)

    assert result.previous_score == 0.0
    assert result.new_score == pytest.approx(0.32)  # 0*0.6 + 0.8*0.4
    assert result.is_pass is True
    assert result.consecutive_failures == 0
    assert result.remediation_triggered is False


async def test_two_consecutive_failures_trigger_remediation(
    db_session, student, make_document, make_topic, set_mastery
) -> None:
    document = await make_document()
    topic = await make_topic(document, "Loops")
    await set_mastery(topic, 0.5, consecutive_failures=1)
    submission = QuizSubmission(study_kit_id=None, answers=[], score=0.1)

    result = await score_and_update_mastery(db_session, student.id, topic.id, submission)

    assert result.is_pass is False
    assert result.consecutive_failures == 2
    assert result.remediation_triggered is True


async def test_large_mastery_drop_triggers_remediation_on_first_failure(
    db_session, student, make_document, make_topic, set_mastery
) -> None:
    document = await make_document()
    topic = await make_topic(document, "Loops")
    await set_mastery(topic, 0.9)
    submission = QuizSubmission(study_kit_id=None, answers=[], score=0.0)

    result = await score_and_update_mastery(db_session, student.id, topic.id, submission)

    assert result.mastery_drop == pytest.approx(0.36)  # 0.9 - (0.9*0.6 + 0*0.4)
    assert result.remediation_triggered is True


async def test_pass_resets_consecutive_failures(
    db_session, student, make_document, make_topic, set_mastery
) -> None:
    document = await make_document()
    topic = await make_topic(document, "Loops")
    await set_mastery(topic, 0.5, consecutive_failures=1)
    submission = QuizSubmission(study_kit_id=None, answers=[], score=0.9)

    result = await score_and_update_mastery(db_session, student.id, topic.id, submission)

    assert result.is_pass is True
    assert result.consecutive_failures == 0


async def test_raises_not_found_for_foreign_topic(db_session) -> None:
    submission = QuizSubmission(study_kit_id=None, answers=[], score=0.5)
    with pytest.raises(NotFoundError):
        await score_and_update_mastery(db_session, uuid.uuid4(), uuid.uuid4(), submission)
