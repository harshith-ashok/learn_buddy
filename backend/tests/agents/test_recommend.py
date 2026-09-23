from datetime import datetime, timedelta

from src.agents.recommend import _exam_urgency, recommend_next_topic
from src.agents.schemas import NoRecommendation, Recommendation


def test_exam_urgency_maxes_out_once_the_exam_date_has_passed() -> None:
    now = datetime(2026, 1, 15)
    overdue = now - timedelta(days=1)

    assert _exam_urgency(overdue, now, window_days=14) == 1.0
    assert _exam_urgency(now, now, window_days=14) == 1.0


async def test_no_topics_returns_no_recommendation(db_session, student) -> None:
    result = await recommend_next_topic(db_session, student.id)

    assert isinstance(result, NoRecommendation)
    assert "upload a document" in result.reason


async def test_recommends_lowest_mastery_ready_topic(
    db_session, student, make_document, make_topic, set_mastery
) -> None:
    document = await make_document()
    low = await make_topic(document, "Loops", position=0)
    high = await make_topic(document, "Recursion", position=1)
    await set_mastery(low, 0.2)
    await set_mastery(high, 0.7)

    result = await recommend_next_topic(db_session, student.id)

    assert isinstance(result, Recommendation)
    assert result.topic_id == low.id


async def test_topic_blocked_by_unmet_prerequisite_is_skipped(
    db_session, student, make_document, make_topic, set_mastery, add_prerequisite
) -> None:
    document = await make_document()
    prereq = await make_topic(document, "Variables", position=0)
    advanced = await make_topic(document, "Loops", position=1)
    await add_prerequisite(advanced, prereq)
    await set_mastery(prereq, 0.1)

    result = await recommend_next_topic(db_session, student.id)

    assert isinstance(result, Recommendation)
    assert result.topic_id == prereq.id


async def test_everything_mastered_and_ready_returns_no_recommendation(
    db_session, student, make_document, make_topic, set_mastery
) -> None:
    document = await make_document()
    topic = await make_topic(document, "Loops")
    await set_mastery(topic, 0.95)

    result = await recommend_next_topic(db_session, student.id)

    assert isinstance(result, NoRecommendation)


async def test_exam_urgency_breaks_a_mastery_tie(
    db_session, student, make_document, make_topic, set_mastery
) -> None:
    soon = await make_document(exam_date=datetime.utcnow() + timedelta(days=1))
    far = await make_document(exam_date=datetime.utcnow() + timedelta(days=60))
    urgent_topic = await make_topic(soon, "Urgent Topic")
    calm_topic = await make_topic(far, "Calm Topic")
    await set_mastery(urgent_topic, 0.2)
    await set_mastery(calm_topic, 0.2)

    result = await recommend_next_topic(db_session, student.id)

    assert isinstance(result, Recommendation)
    assert result.topic_id == urgent_topic.id
