import os

import pytest

from src.core.config import get_settings
from src.core.llm_client import LLMClient
from src.ingestion.schemas import ParsedDocument, ParsedSection, TopicExtractionResult
from src.ingestion.topic_extractor import extract_topics

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
async def test_embed_returns_real_vectors(llm_client: LLMClient) -> None:
    """`OLLAMA_EMBED_MODEL` round-trips a real embedding, not a mock."""
    vectors = await llm_client.embed(["Binary search runs in O(log n) time."])

    assert len(vectors) == 1
    assert len(vectors[0]) > 0
    assert all(isinstance(value, float) for value in vectors[0])


@pytest.mark.skipif(not _RUN_LIVE, reason=_SKIP_REASON)
async def test_extract_topics_returns_validated_structure(llm_client: LLMClient) -> None:
    """`OLLAMA_MODEL` returns a `TopicExtractionResult`-shaped response for real.

    A schema-validation failure here (e.g. the bare-array response noted in
    `wiki/phases/phase-2-ingestion.md`'s footnote) is a real signal, not
    flakiness to retry past — see `TODO.md` Phase 2 follow-ups for what to
    do with that result.
    """
    document = ParsedDocument(
        title="Intro to Sorting",
        sections=[
            ParsedSection(
                heading="Bubble Sort",
                level=1,
                text="Bubble sort repeatedly swaps adjacent out-of-order elements until the list is sorted.",
            ),
            ParsedSection(
                heading="Merge Sort",
                level=1,
                text=(
                    "Merge sort splits the list in half, recursively sorts each half, then merges "
                    "the results. It relies on the same element-comparison idea used in bubble sort."
                ),
            ),
        ],
    )

    result = await extract_topics(document, llm_client)

    assert isinstance(result, TopicExtractionResult)
    assert len(result.topics) > 0
    assert all(topic.name for topic in result.topics)
