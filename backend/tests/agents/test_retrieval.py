import uuid

import pytest

from src.agents.retrieval import retrieve_context
from src.db.models import Topic


@pytest.fixture
def topic() -> Topic:
    return Topic(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        name="Binary Search",
        description="Searching a sorted array by halving the search space",
        position=0,
    )


async def test_retrieve_context_covered_by_semantic_similarity(
    fake_agent_llm, test_vectorstore, topic
) -> None:
    student_id = uuid.uuid4()
    document_id = uuid.uuid4()
    query = "how does binary search work"
    fake_agent_llm.embeddings[query] = [1.0, 0.0, 0.0, 0.0]

    collection = test_vectorstore.get_or_create_collection(str(student_id))
    collection.add(
        ids=[f"{document_id}:0"],
        embeddings=[[1.0, 0.0, 0.0, 0.0]],
        documents=["Binary search repeatedly halves the search interval."],
        metadatas=[{"document_id": str(document_id), "section_heading": "Binary Search"}],
    )

    result = await retrieve_context(query, student_id, topic, fake_agent_llm, test_vectorstore)

    assert result.covered is True
    assert result.chunks[0].chunk_id == f"{document_id}:0"
    assert result.chunks[0].similarity == pytest.approx(1.0)


async def test_retrieve_context_empty_collection_is_not_covered(
    fake_agent_llm, test_vectorstore, topic
) -> None:
    result = await retrieve_context("anything at all", uuid.uuid4(), topic, fake_agent_llm, test_vectorstore)

    assert result.covered is False
    assert result.chunks == []


async def test_retrieve_context_below_threshold_and_no_keyword_match_is_not_covered(
    fake_agent_llm, test_vectorstore, topic
) -> None:
    student_id = uuid.uuid4()
    document_id = uuid.uuid4()
    query = "explain quantum entanglement"
    fake_agent_llm.embeddings[query] = [0.0, 1.0, 0.0, 0.0]

    collection = test_vectorstore.get_or_create_collection(str(student_id))
    collection.add(
        ids=[f"{document_id}:0", f"{document_id}:1"],
        embeddings=[[1.0, 0.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0]],
        documents=[
            "Binary search repeatedly halves the search interval.",
            "Merge sort splits and recombines a list.",
        ],
        metadatas=[
            {"document_id": str(document_id), "section_heading": "Binary Search"},
            {"document_id": str(document_id), "section_heading": "Merge Sort"},
        ],
    )

    result = await retrieve_context(query, student_id, topic, fake_agent_llm, test_vectorstore)

    assert result.covered is False
    assert result.chunks == []


async def test_retrieve_context_keyword_fallback_recovers_low_similarity_match(
    fake_agent_llm, test_vectorstore, topic
) -> None:
    student_id = uuid.uuid4()
    document_id = uuid.uuid4()
    query = "binary search halving interval"
    fake_agent_llm.embeddings[query] = [0.0, 0.0, 0.0, 1.0]  # orthogonal to both stored chunks

    collection = test_vectorstore.get_or_create_collection(str(student_id))
    collection.add(
        ids=[f"{document_id}:0", f"{document_id}:1"],
        embeddings=[[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]],
        documents=[
            "binary search halving interval binary search halving interval sorted array",
            "totally unrelated content about photosynthesis in plants",
        ],
        metadatas=[
            {"document_id": str(document_id), "section_heading": "Binary Search"},
            {"document_id": str(document_id), "section_heading": "Unrelated"},
        ],
    )

    result = await retrieve_context(query, student_id, topic, fake_agent_llm, test_vectorstore)

    assert result.covered is True
    assert result.chunks[0].chunk_id == f"{document_id}:0"
