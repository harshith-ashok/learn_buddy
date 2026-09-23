import uuid

from src.ingestion.embedder import embed_and_store_chunks
from src.ingestion.schemas import Chunk


def _chunks(n: int) -> list[Chunk]:
    return [Chunk(order=i, section_heading="Intro", text=f"chunk text {i}", token_count=3) for i in range(n)]


async def test_embed_and_store_writes_all_chunks(fake_llm_client, test_vectorstore) -> None:
    student_id = uuid.uuid4()
    document_id = uuid.uuid4()

    await embed_and_store_chunks(_chunks(5), student_id, document_id, fake_llm_client, test_vectorstore)

    collection = test_vectorstore.get_or_create_collection(str(student_id))
    assert collection.count() == 5


async def test_reembedding_same_document_replaces_not_duplicates(fake_llm_client, test_vectorstore) -> None:
    student_id = uuid.uuid4()
    document_id = uuid.uuid4()

    await embed_and_store_chunks(_chunks(5), student_id, document_id, fake_llm_client, test_vectorstore)
    await embed_and_store_chunks(_chunks(2), student_id, document_id, fake_llm_client, test_vectorstore)

    collection = test_vectorstore.get_or_create_collection(str(student_id))
    assert collection.count() == 2


async def test_embedding_batches_respect_configured_batch_size(fake_llm_client, test_vectorstore) -> None:
    settings = test_vectorstore._settings.model_copy(update={"embedding_batch_size": 2})
    student_id = uuid.uuid4()
    document_id = uuid.uuid4()

    await embed_and_store_chunks(
        _chunks(5), student_id, document_id, fake_llm_client, test_vectorstore, settings
    )

    assert [len(batch) for batch in fake_llm_client.embed_calls] == [2, 2, 1]


async def test_empty_chunk_list_clears_without_calling_embed(fake_llm_client, test_vectorstore) -> None:
    student_id = uuid.uuid4()
    document_id = uuid.uuid4()

    await embed_and_store_chunks(_chunks(3), student_id, document_id, fake_llm_client, test_vectorstore)
    await embed_and_store_chunks([], student_id, document_id, fake_llm_client, test_vectorstore)

    collection = test_vectorstore.get_or_create_collection(str(student_id))
    assert collection.count() == 0
    assert fake_llm_client.embed_calls == [[c.text for c in _chunks(3)]]
