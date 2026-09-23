from src.agents.remediation import build_remediation_plan
from src.agents.schemas import MasteryUpdateResult


async def test_remediation_plan_lists_weak_prerequisite_first(
    db_session, student, make_document, make_topic, set_mastery, add_prerequisite
) -> None:
    document = await make_document()
    prereq = await make_topic(document, "Variables", position=0)
    topic = await make_topic(document, "Loops", position=1)
    await add_prerequisite(topic, prereq)
    await set_mastery(prereq, 0.2)

    mastery_result = MasteryUpdateResult(
        topic_id=topic.id,
        previous_score=0.5,
        new_score=0.3,
        is_pass=False,
        consecutive_failures=2,
        mastery_drop=0.2,
        remediation_triggered=True,
    )

    plan = await build_remediation_plan(db_session, student.id, topic.id, mastery_result)

    assert "Variables" in plan.suggested_actions[0]
    assert "2 quizzes in a row" in plan.reason
    assert "20%" in plan.reason


async def test_remediation_plan_without_weak_prerequisites_still_suggests_review(
    db_session, student, make_document, make_topic
) -> None:
    document = await make_document()
    topic = await make_topic(document, "Loops")
    mastery_result = MasteryUpdateResult(
        topic_id=topic.id,
        previous_score=0.9,
        new_score=0.5,
        is_pass=False,
        consecutive_failures=1,
        mastery_drop=0.4,
        remediation_triggered=True,
    )

    plan = await build_remediation_plan(db_session, student.id, topic.id, mastery_result)

    assert any("Regenerate a fresh study kit" in action for action in plan.suggested_actions)
    assert "40%" in plan.reason
    assert "quizzes in a row" not in plan.reason
