import uuid
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.llm_client import LLMClient, get_llm_client
from src.core.logging import get_logger
from src.core.vectorstore import VectorStoreClient, get_vectorstore_client
from src.db.models import Document, DocumentStatus, Topic
from src.db.session import async_session_factory
from src.ingestion import storage
from src.ingestion.chunker import chunk_document
from src.ingestion.embedder import embed_and_store_chunks
from src.ingestion.parsers import parse_document
from src.ingestion.topic_extractor import extract_topics, persist_topics

logger = get_logger(__name__)


async def _clear_existing_topics(db: AsyncSession, document_id: uuid.UUID) -> None:
    """Delete this document's topics before re-persisting a fresh extraction.

    Cascades (DB-level `ON DELETE CASCADE`) also remove that document's
    `subtopics` and `topic_prerequisites`, and any `mastery_scores`,
    `study_kits`, or `quiz_attempts` tied to those topics. A re-upload is
    treated as a full replace of this document's derived data, not a
    diff/merge against the previous extraction — see
    `wiki/decisions/0003-reupload-replaces-topics.md`.
    """
    await db.execute(delete(Topic).where(Topic.document_id == document_id))
    await db.flush()


async def process_document(
    document_id: uuid.UUID,
    llm_client: LLMClient | None = None,
    vectorstore: VectorStoreClient | None = None,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> None:
    """Run the full ingestion pipeline for one document: parse, chunk, embed, extract topics.

    Opens its own DB session (via `session_factory`, defaulting to the
    process-wide one) — callers running this from a `BackgroundTasks` job
    (after the request's session has closed) or any other out-of-request
    context can call it directly. Tests override `session_factory` (via
    `SessionFactoryDep`) to point this at the same transaction their DB
    fixtures use.
    """
    llm_client = llm_client or get_llm_client()
    vectorstore = vectorstore or get_vectorstore_client()
    session_factory = session_factory or async_session_factory

    async with session_factory() as db:
        document = await db.get(Document, document_id)
        if document is None:
            logger.error(
                "process_document called for a missing document", extra={"document_id": str(document_id)}
            )
            return

        try:
            document.status = DocumentStatus.PROCESSING
            await db.flush()

            content = await storage.read_file(Path(document.storage_path))
            parsed = parse_document(document.filename, content)

            chunks = chunk_document(parsed)
            await embed_and_store_chunks(chunks, document.student_id, document.id, llm_client, vectorstore)

            await _clear_existing_topics(db, document.id)
            extraction = await extract_topics(parsed, llm_client)
            await persist_topics(db, document.id, extraction)

            document.status = DocumentStatus.DONE
            await db.commit()
            logger.info(
                "Document ingestion complete",
                extra={
                    "document_id": str(document_id),
                    "chunk_count": len(chunks),
                    "topic_count": len(extraction.topics),
                },
            )
        except Exception:
            logger.exception("Document ingestion failed", extra={"document_id": str(document_id)})
            await db.rollback()
            document.status = DocumentStatus.FAILED
            db.add(document)
            await db.commit()
            raise
