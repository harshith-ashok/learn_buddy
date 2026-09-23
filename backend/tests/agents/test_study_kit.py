import uuid

import pytest

from src.agents.schemas import Flashcard, FlashcardsContent, NotCovered, StudyKitResult
from src.agents.study_kit import generate_study_kit, persist_study_kit
from src.core.errors import NotFoundError
from src.db.models import StudyKitType


async def test_generate_study_kit_not_covered_skips_the_model(
    db_session, student, make_document, make_topic, fake_agent_llm, test_vectorstore
) -> None:
    document = await make_document()
    topic = await make_topic(document, "Loops", description="For and while loops")

    result = await generate_study_kit(
        db_session, student.id, topic.id, StudyKitType.FLASHCARDS, fake_agent_llm, test_vectorstore
    )

    assert isinstance(result, NotCovered)
    assert fake_agent_llm.chat_calls == []


async def test_generate_study_kit_returns_grounded_content_and_persists(
    db_session, student, make_document, make_topic, fake_agent_llm, test_vectorstore
) -> None:
    document = await make_document()
    topic = await make_topic(document, "Loops", description="For and while loops")
    query = f"{topic.name}. {topic.description}"
    fake_agent_llm.embeddings[query] = [1.0, 0.0]

    collection = test_vectorstore.get_or_create_collection(str(student.id))
    collection.add(
        ids=[f"{document.id}:0"],
        embeddings=[[1.0, 0.0]],
        documents=["A for loop repeats a block a fixed number of times."],
        metadatas=[{"document_id": str(document.id), "section_heading": "Loops"}],
    )
    expected = FlashcardsContent(
        cards=[
            Flashcard(
                question="What is a for loop?",
                answer="A loop that repeats a fixed number of times.",
                source_chunk_ids=[f"{document.id}:0"],
            )
        ]
    )
    fake_agent_llm.chat_responses[FlashcardsContent] = expected

    result = await generate_study_kit(
        db_session, student.id, topic.id, StudyKitType.FLASHCARDS, fake_agent_llm, test_vectorstore
    )

    assert isinstance(result, StudyKitResult)
    assert result.content == expected
    assert result.source_chunk_ids == [f"{document.id}:0"]

    study_kit = await persist_study_kit(db_session, student.id, topic.id, result)

    assert study_kit.kit_type == StudyKitType.FLASHCARDS
    assert study_kit.source_chunk_ids == [f"{document.id}:0"]
    assert study_kit.content["cards"][0]["question"] == "What is a for loop?"


async def test_generate_study_kit_raises_not_found_for_foreign_topic(
    db_session, fake_agent_llm, test_vectorstore
) -> None:
    with pytest.raises(NotFoundError):
        await generate_study_kit(
            db_session, uuid.uuid4(), uuid.uuid4(), StudyKitType.SUMMARY, fake_agent_llm, test_vectorstore
        )
