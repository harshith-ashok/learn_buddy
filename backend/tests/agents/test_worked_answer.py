import uuid

import pytest

from src.agents.schemas import WorkedAnswerGradeContent, WorkedStepFeedback, WorkedStepVerdict
from src.agents.worked_answer import grade_worked_answer
from src.core.errors import AppError, NotFoundError
from src.db.models import StudyKit, StudyKitType

_PROBLEM_GUIDE_CONTENT = {
    "problems": [
        {
            "prompt": "A car accelerates from 0 to 20 m/s in 4 seconds. Find its acceleration.",
            "steps": [
                {"text": "acceleration = change in velocity / time", "source_chunk_ids": []},
                {"text": "a = (20 - 0) / 4", "source_chunk_ids": []},
                {"text": "a = 5 m/s^2", "source_chunk_ids": []},
            ],
        }
    ],
    "formulas": [],
}


@pytest.fixture
async def problem_guide_kit(db_session, student, make_document, make_topic) -> StudyKit:
    document = await make_document()
    topic = await make_topic(document, "Kinematics", description="Motion and acceleration")
    kit = StudyKit(
        student_id=student.id,
        topic_id=topic.id,
        kit_type=StudyKitType.PROBLEM_GUIDE,
        content=_PROBLEM_GUIDE_CONTENT,
        source_chunk_ids=[],
    )
    db_session.add(kit)
    await db_session.flush()
    return kit


async def test_grades_worked_answer_updates_mastery_and_persists_attempt(
    db_session, student, problem_guide_kit, fake_agent_llm
) -> None:
    fake_agent_llm.chat_responses[WorkedAnswerGradeContent] = WorkedAnswerGradeContent(
        gradable=True,
        is_correct=True,
        accuracy_score=1.0,
        overall_feedback="All steps correct.",
        step_feedback=[
            WorkedStepFeedback(
                step_number=1, student_text="a = 20/4", verdict=WorkedStepVerdict.CORRECT, feedback="Right."
            )
        ],
        first_error_step=None,
    )

    result = await grade_worked_answer(
        db_session, student.id, problem_guide_kit.id, 0, "a = 20/4 = 5 m/s^2", fake_agent_llm
    )

    assert result.covered is True
    assert result.is_correct is True
    assert result.mastery is not None
    assert result.mastery.new_score == pytest.approx(0.4)  # 0*0.6 + 1.0*0.4


async def test_model_self_refusal_skips_mastery_update(
    db_session, student, problem_guide_kit, fake_agent_llm
) -> None:
    fake_agent_llm.chat_responses[WorkedAnswerGradeContent] = WorkedAnswerGradeContent(gradable=False)

    result = await grade_worked_answer(
        db_session, student.id, problem_guide_kit.id, 0, "asdf", fake_agent_llm
    )

    assert result.covered is False
    assert result.mastery is None


async def test_first_error_step_is_reported(db_session, student, problem_guide_kit, fake_agent_llm) -> None:
    fake_agent_llm.chat_responses[WorkedAnswerGradeContent] = WorkedAnswerGradeContent(
        gradable=True,
        is_correct=False,
        accuracy_score=0.33,
        overall_feedback="Divided wrong.",
        step_feedback=[
            WorkedStepFeedback(
                step_number=1,
                student_text="a = v/t",
                verdict=WorkedStepVerdict.CORRECT,
                feedback="Right formula.",
            ),
            WorkedStepFeedback(
                step_number=2,
                student_text="a = 20*4",
                verdict=WorkedStepVerdict.INCORRECT,
                feedback="Should divide, not multiply.",
            ),
        ],
        first_error_step=2,
    )

    result = await grade_worked_answer(
        db_session, student.id, problem_guide_kit.id, 0, "a = v/t\na = 20*4 = 80", fake_agent_llm
    )

    assert result.first_error_step == 2
    assert result.is_correct is False


async def test_rejects_an_out_of_range_problem_index(
    db_session, student, problem_guide_kit, fake_agent_llm
) -> None:
    with pytest.raises(AppError):
        await grade_worked_answer(db_session, student.id, problem_guide_kit.id, 5, "work", fake_agent_llm)


async def test_rejects_a_non_problem_guide_kit(
    db_session, student, make_document, make_topic, fake_agent_llm
) -> None:
    document = await make_document()
    topic = await make_topic(document, "Loops")
    quiz_kit = StudyKit(
        student_id=student.id,
        topic_id=topic.id,
        kit_type=StudyKitType.QUIZ,
        content={"questions": []},
        source_chunk_ids=[],
    )
    db_session.add(quiz_kit)
    await db_session.flush()

    with pytest.raises(AppError):
        await grade_worked_answer(db_session, student.id, quiz_kit.id, 0, "work", fake_agent_llm)


async def test_raises_not_found_for_a_foreign_study_kit(db_session, fake_agent_llm) -> None:
    with pytest.raises(NotFoundError):
        await grade_worked_answer(db_session, uuid.uuid4(), uuid.uuid4(), 0, "work", fake_agent_llm)
