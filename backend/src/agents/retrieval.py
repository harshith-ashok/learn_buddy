import uuid

from src.agents.schemas import RetrievalResult, RetrievedChunk
from src.agents.text_scoring import bm25_scores, normalize, tokenize, topic_overlap_score
from src.core.config import Settings, get_settings
from src.core.llm_client import LLMClient
from src.core.logging import get_logger
from src.core.vectorstore import VectorStoreClient
from src.db.models import Topic

logger = get_logger(__name__)


async def retrieve_context(
    query: str,
    student_id: uuid.UUID,
    topic: Topic,
    llm_client: LLMClient,
    vectorstore: VectorStoreClient,
    settings: Settings | None = None,
    document_id: uuid.UUID | None = None,
) -> RetrievalResult:
    """Retrieve grounding chunks for `query`, scoped to `student_id` and re-ranked against `topic`.

    Semantic search runs first; a keyword/BM25 pass over the same
    candidate pool is folded in whenever it beats the semantic score for
    a given chunk (the fallback the pipeline needs when a query's wording
    doesn't overlap the source material's, which vector similarity alone
    can miss). `covered=False` means nothing — semantic or keyword —
    clears `retrieval_similarity_threshold`; callers must not generate
    from that, see `agents.schemas.NotCovered`.

    `document_id`, when given, restricts the candidate pool to chunks from
    that document via Chroma's `where` filter — the per-topic chat guardrail
    ("only answer from this topic's own material") needs this; study-kit
    generation leaves it `None` and searches the student's whole corpus.
    """
    settings = settings or get_settings()
    collection = vectorstore.get_or_create_collection(str(student_id))
    where = {"document_id": str(document_id)} if document_id is not None else None
    chunk_count = collection.count()
    if chunk_count == 0:
        return RetrievalResult(chunks=[], covered=False)

    [query_embedding] = await llm_client.embed([query])
    pool_size = min(settings.retrieval_candidate_pool, chunk_count)
    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=pool_size,
        where=where,  # pyright: ignore[reportArgumentType]
        include=["documents", "metadatas", "distances"],  # pyright: ignore[reportArgumentType] -- chromadb-client's `Include` stub wants its own enum, not plain strings
    )

    # chromadb-client types every `include`d field as optional even though
    # requesting it (above) always populates it — safe to index directly.
    ids = result["ids"][0]
    documents = result["documents"][0]  # pyright: ignore[reportOptionalSubscript]
    metadatas = result["metadatas"][0]  # pyright: ignore[reportOptionalSubscript]
    distances = result["distances"][0]  # pyright: ignore[reportOptionalSubscript]
    similarities = [max(0.0, 1.0 - distance) for distance in distances]

    query_tokens = tokenize(query)
    doc_tokens = [tokenize(doc) for doc in documents]
    keyword_scores = normalize(bm25_scores(query_tokens, doc_tokens))

    relevance_scores = [max(sem, kw) for sem, kw in zip(similarities, keyword_scores, strict=True)]
    covered = bool(relevance_scores) and max(relevance_scores) >= settings.retrieval_similarity_threshold
    if not covered:
        logger.info(
            "Retrieval found nothing above the similarity threshold",
            extra={"query": query[:200], "best_relevance": max(relevance_scores, default=0.0)},
        )
        return RetrievalResult(chunks=[], covered=False)

    scored: list[tuple[float, RetrievedChunk]] = []
    for chunk_id, doc, meta, relevance, tokens in zip(
        ids, documents, metadatas, relevance_scores, doc_tokens, strict=True
    ):
        combined = relevance * 0.7 + topic_overlap_score(topic, tokens) * 0.3
        scored.append(
            (
                combined,
                RetrievedChunk(
                    chunk_id=chunk_id,
                    # chromadb-client types a metadata value as str|int|float|bool;
                    # embedder.py always writes document_id/section_heading as str.
                    document_id=uuid.UUID(meta["document_id"]),  # pyright: ignore[reportArgumentType]
                    text=doc,
                    section_heading=meta.get("section_heading") or None,  # pyright: ignore[reportArgumentType]
                    similarity=relevance,
                ),
            )
        )

    scored.sort(key=lambda pair: pair[0], reverse=True)
    top_chunks = [chunk for _, chunk in scored[: settings.retrieval_rerank_top_n]]
    return RetrievalResult(chunks=top_chunks, covered=True)
