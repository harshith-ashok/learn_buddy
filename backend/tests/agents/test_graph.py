import uuid

from src.agents.graph import run_agent
from src.agents.schemas import (
    Flashcard,
    FlashcardsContent,
    Intent,
    IntentClassification,
    QuizAnswer,
    QuizSubmission,
)
from src.db.models import StudyKitType


async def test_run_agent_routes_recommend_next(
    db_session, student, make_document, make_topic, set_mastery, fake_agent_llm, test_vectorstore
) -> None:
    document = await make_document()
    topic = await make_topic(document, "Loops")
    await set_mastery(topic, 0.1)
    fake_agent_llm.chat_responses[IntentClassification] = IntentClassification(
        intent=Intent.RECOMMEND_NEXT, confidence=0.9
    )

    result = await run_agent(db_session, fake_agent_llm, test_vectorstore, "what next?", student.id)

    assert result["topic_id"] == str(topic.id)


async def test_run_agent_routes_generate_study_kit_not_covered(
    db_session, student, make_document, make_topic, fake_agent_llm, test_vectorstore
) -> None:
    document = await make_document()
    topic = await make_topic(document, "Loops")
    fake_agent_llm.chat_responses[IntentClassification] = IntentClassification(
        intent=Intent.GENERATE_STUDY_KIT, confidence=0.9
    )

    result = await run_agent(
        db_session,
        fake_agent_llm,
        test_vectorstore,
        "give me flashcards on loops",
        student.id,
        topic_id=topic.id,
        kit_type=StudyKitType.FLASHCARDS,
    )

    assert "isn't covered" in result["message"].lower()


async def test_run_agent_routes_generate_study_kit_and_persists_it(
    db_session, student, make_document, make_topic, fake_agent_llm, test_vectorstore
) -> None:
    document = await make_document()
    topic = await make_topic(document, "Loops", description="For and while loops")
    query = f"{topic.name}. {topic.description}"
    fake_agent_llm.embeddings[query] = [1.0, 0.0]
    collection = test_vectorstore.get_or_create_collection(str(student.id))
    collection.add(
        ids=[f"{uuid.uuid4()}:0"],
        embeddings=[[1.0, 0.0]],
        documents=["A for loop repeats a block a fixed number of times."],
        metadatas=[{"document_id": str(document.id), "section_heading": "Loops"}],
    )
    fake_agent_llm.chat_responses[IntentClassification] = IntentClassification(
        intent=Intent.GENERATE_STUDY_KIT, confidence=0.9
    )
    fake_agent_llm.chat_responses[FlashcardsContent] = FlashcardsContent(
        cards=[Flashcard(question="Q", answer="A", source_chunk_ids=[])]
    )

    result = await run_agent(
        db_session,
        fake_agent_llm,
        test_vectorstore,
        "give me flashcards on loops",
        student.id,
        topic_id=topic.id,
        kit_type=StudyKitType.FLASHCARDS,
    )

    assert result["kit_type"] == "flashcards"
    assert "study_kit_id" in result


async def test_run_agent_generate_study_kit_without_topic_id_errors(
    db_session, student, fake_agent_llm, test_vectorstore
) -> None:
    fake_agent_llm.chat_responses[IntentClassification] = IntentClassification(
        intent=Intent.GENERATE_STUDY_KIT, confidence=0.9
    )

    result = await run_agent(db_session, fake_agent_llm, test_vectorstore, "flashcards please", student.id)

    assert result == {}


async def test_run_agent_submit_quiz_without_submission_errors(
    db_session, student, make_document, make_topic, fake_agent_llm, test_vectorstore
) -> None:
    document = await make_document()
    topic = await make_topic(document, "Loops")
    fake_agent_llm.chat_responses[IntentClassification] = IntentClassification(
        intent=Intent.SUBMIT_QUIZ, confidence=0.9
    )

    result = await run_agent(
        db_session, fake_agent_llm, test_vectorstore, "I took the quiz", student.id, topic_id=topic.id
    )

    assert result == {}


async def test_run_agent_routes_submit_quiz_and_triggers_remediation(
    db_session, student, make_document, make_topic, set_mastery, fake_agent_llm, test_vectorstore
) -> None:
    document = await make_document()
    topic = await make_topic(document, "Loops")
    await set_mastery(topic, 0.5, consecutive_failures=1)
    fake_agent_llm.chat_responses[IntentClassification] = IntentClassification(
        intent=Intent.SUBMIT_QUIZ, confidence=0.9
    )
    submission = QuizSubmission(
        study_kit_id=None, answers=[QuizAnswer(question_index=0, selected_index=0)], score=0.1
    )

    result = await run_agent(
        db_session,
        fake_agent_llm,
        test_vectorstore,
        "I got a 10%",
        student.id,
        topic_id=topic.id,
        quiz_submission=submission,
    )

    assert result["remediation_triggered"] is True
    assert result["remediation"]["topic_id"] == str(topic.id)


async def test_run_agent_routes_other_with_a_static_fallback(
    db_session, student, fake_agent_llm, test_vectorstore
) -> None:
    fake_agent_llm.chat_responses[IntentClassification] = IntentClassification(
        intent=Intent.OTHER, confidence=0.5
    )

    result = await run_agent(db_session, fake_agent_llm, test_vectorstore, "hello there", student.id)

    assert "help" in result["message"].lower()
    assert fake_agent_llm.chat_calls == [IntentClassification]
