import uuid

from src.core.config import Settings, get_settings
from src.core.llm_client import LLMClient
from src.core.vectorstore import VectorStoreClient
from src.ingestion.schemas import Chunk


def _batched(items: list[Chunk], size: int) -> list[list[Chunk]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


async def embed_and_store_chunks(
    chunks: list[Chunk],
    student_id: uuid.UUID,
    document_id: uuid.UUID,
    llm_client: LLMClient,
    vectorstore: VectorStoreClient,
    settings: Settings | None = None,
) -> None:
    """Embed `chunks` in batches and upsert them into the student's Chroma collection.

    Any existing chunks for `document_id` are cleared first, so re-running
    this for a re-uploaded document replaces rather than duplicates them
    (see `ingestion.pipeline`).
    """
    settings = settings or get_settings()
    collection = vectorstore.get_or_create_collection(str(student_id))
    collection.delete(where={"document_id": str(document_id)})

    if not chunks:
        return

    for batch in _batched(chunks, settings.embedding_batch_size):
        embeddings = await llm_client.embed([chunk.text for chunk in batch])
        collection.add(
            ids=[f"{document_id}:{chunk.order}" for chunk in batch],
            # chromadb-client's stub wants its own Embedding/ndarray type, not
            # plain list[list[float]] — a plain nested list is what its own
            # runtime API actually accepts.
            embeddings=embeddings,  # pyright: ignore[reportArgumentType]
            documents=[chunk.text for chunk in batch],
            metadatas=[
                {
                    "document_id": str(document_id),
                    "order": chunk.order,
                    "section_heading": chunk.section_heading or "",
                    "token_count": chunk.token_count,
                }
                for chunk in batch
            ],
        )
