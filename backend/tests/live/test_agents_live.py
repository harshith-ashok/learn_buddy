import os
import uuid

import pytest

from src.agents.classify import classify_intent
from src.agents.retrieval import retrieve_context
from src.agents.schemas import Intent
from src.core.config import get_settings
from src.core.llm_client import LLMClient
from src.core.vectorstore import get_vectorstore_client
from src.db.models import Topic

pytestmark = pytest.mark.live_model

_RUN_LIVE = os.getenv("RUN_LIVE_LLM_TESTS") == "1"
_SKIP_REASON = (
    "Opt-in only: hits the real Ollama endpoint configured via OLLAMA_BASE_URL/"
    "OLLAMA_API_KEY in .env. Set RUN_LIVE_LLM_TESTS=1 to run (see wiki/runbook.md)."
)


@pytest.fixture
async def llm_client():
    client = LLMClient(get_settings())
    yield client
    await client.aclose()


@pytest.mark.skipif(not _RUN_LIVE, reason=_SKIP_REASON)
async def test_classify_intent_recognizes_a_clear_recommendation_request(llm_client: LLMClient) -> None:
    """`OLLAMA_MODEL` classifies an unambiguous message correctly for real.

    A wrong or unparseable result here is real signal about the
    classifier's reliability against the live endpoint, not flakiness.
    """
    result = await classify_intent("What topic should I study next?", llm_client)

    assert result.intent is Intent.RECOMMEND_NEXT


@pytest.mark.skipif(not _RUN_LIVE, reason=_SKIP_REASON)
async def test_retrieve_context_round_trips_against_real_embeddings(llm_client: LLMClient) -> None:
    """A real embedding for a query finds a real embedding for its own matching chunk."""
    settings = get_settings()
    vectorstore = get_vectorstore_client()
    student_id = uuid.uuid4()
    document_id = uuid.uuid4()
    topic = Topic(
        id=uuid.uuid4(),
        document_id=document_id,
        name="Binary Search",
        description="Searching a sorted array by halving the search interval",
        position=0,
    )

    collection = vectorstore.get_or_create_collection(str(student_id))
    try:
        text = "Binary search repeatedly halves the search interval to find a target in a sorted array."
        [embedding] = await llm_client.embed([text])
        collection.add(
            ids=[f"{document_id}:0"],
            embeddings=[embedding],
            documents=[text],
            metadatas=[{"document_id": str(document_id), "section_heading": "Binary Search"}],
        )

        result = await retrieve_context(
            "how does binary search work", student_id, topic, llm_client, vectorstore, settings
        )

        assert result.covered is True
        assert result.chunks
    finally:
        vectorstore.delete_collection(str(student_id))
