from functools import lru_cache

import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection

from src.core.config import Settings, get_settings


class VectorStoreClient:
    """Owns the Chroma connection and collection-naming convention.

    Nothing outside `src.core` and `src.ingestion`/`src.agents.retrieval`
    should talk to Chroma directly — collection names and connection setup
    live here only.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: ClientAPI = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)

    def collection_name(self, student_id: str) -> str:
        """Chunks are scoped per-student: one collection per learner.

        Keeps retrieval trivially scoped (no per-query student_id filter to
        forget) and makes per-user export/delete a single collection drop.
        """
        return f"{self._settings.chroma_collection_prefix}_student_{student_id}"

    def get_or_create_collection(self, student_id: str) -> Collection:
        # Cosine space (not Chroma's default squared-L2) so retrieval can
        # threshold on a bounded, well-understood similarity score — see
        # wiki/decisions/0005-cosine-similarity-for-retrieval-guardrail.md.
        return self._client.get_or_create_collection(
            name=self.collection_name(student_id), metadata={"hnsw:space": "cosine"}
        )

    def delete_collection(self, student_id: str) -> None:
        """Drop a student's entire collection (e.g. account/data deletion)."""
        self._client.delete_collection(name=self.collection_name(student_id))

    def heartbeat(self) -> int:
        return self._client.heartbeat()


@lru_cache
def get_vectorstore_client() -> VectorStoreClient:
    return VectorStoreClient(get_settings())
