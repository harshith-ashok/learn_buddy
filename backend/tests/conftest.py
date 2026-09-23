import hashlib
import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import get_settings
from src.core.vectorstore import VectorStoreClient
from src.db.base import Base
from src.db.models import *  # noqa: F401,F403 -- registers every model on Base.metadata
from src.db.session import get_db
from src.ingestion.schemas import TopicExtractionResult
from src.main import app


def _split_db_name(database_url: str) -> tuple[str, str]:
    """Return `(url without the trailing /<db>, db name)`."""
    base_url, _, db_name = database_url.rpartition("/")
    return base_url, db_name


@pytest.fixture(scope="session", autouse=True)
def _isolated_storage_dir(tmp_path_factory: pytest.TempPathFactory) -> None:
    """Redirect uploaded-file storage into a temp dir for the whole test session.

    Without this, `api.documents.upload_document` (which reads
    `storage_dir` fresh off the real, cached `Settings` — not something a
    DB/LLM fixture override touches) writes real files under the repo's
    `backend/storage/` on every integration test run.
    """
    get_settings().storage_dir = str(tmp_path_factory.mktemp("storage"))


@pytest_asyncio.fixture(scope="session")
async def test_engine() -> AsyncGenerator[AsyncEngine]:
    """Session-scoped engine bound to a dedicated `<db>_test` database.

    Creating a separate database (rather than reusing the dev one, or a
    schema) means running the suite can never clobber local dev data, and
    each run starts from a clean, migration-equivalent schema.
    """
    settings = get_settings()
    base_url, db_name = _split_db_name(settings.database_url)
    test_db_name = f"{db_name}_test"
    test_db_url = f"{base_url}/{test_db_name}"

    admin_engine = create_async_engine(settings.database_url, isolation_level="AUTOCOMMIT")
    async with admin_engine.connect() as conn:
        await conn.execute(text(f'DROP DATABASE IF EXISTS "{test_db_name}" WITH (FORCE)'))
        await conn.execute(text(f'CREATE DATABASE "{test_db_name}"'))
    await admin_engine.dispose()

    engine = create_async_engine(test_db_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession]:
    """A session whose changes are rolled back after the test.

    Wraps a connection-level transaction and binds the session to it with
    `join_transaction_mode="create_savepoint"`, so `session.commit()` calls
    inside the code under test don't escape the outer rollback.
    """
    async with test_engine.connect() as conn:
        outer_transaction = await conn.begin()
        session_factory = async_sessionmaker(
            bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        async with session_factory() as session:
            yield session
        await outer_transaction.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    """An HTTP client against the app with `get_db` overridden to `db_session`."""

    async def _get_db_override() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = _get_db_override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


class FakeLLMClient:
    """A stand-in for `LLMClient` — deterministic, no network calls.

    Matches the subset of `LLMClient`'s interface the ingestion pipeline
    uses (`embed`, `chat_json`), per the project's "no live model calls in
    the test suite" testing philosophy (see `wiki/runbook.md`).
    """

    def __init__(self, extraction: TopicExtractionResult | None = None) -> None:
        self.extraction = extraction or TopicExtractionResult(topics=[])
        self.embed_calls: list[list[str]] = []
        self.chat_calls = 0

    async def embed(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        self.embed_calls.append(texts)
        return [[float(len(text) % 11), float(index)] for index, text in enumerate(texts)]

    async def chat_json(self, messages: list[dict[str, str]], schema: type, model: str | None = None):
        self.chat_calls += 1
        assert schema is TopicExtractionResult
        return self.extraction


@pytest.fixture
def fake_llm_client() -> FakeLLMClient:
    return FakeLLMClient()


@pytest_asyncio.fixture
async def test_vectorstore() -> AsyncGenerator[VectorStoreClient]:
    """A `VectorStoreClient` under a per-test collection prefix, cleaned up after."""
    settings = get_settings().model_copy(update={"chroma_collection_prefix": f"test_{uuid.uuid4().hex[:12]}"})
    client = VectorStoreClient(settings)

    yield client

    for collection in client._client.list_collections():
        if collection.name.startswith(settings.chroma_collection_prefix):
            client._client.delete_collection(name=collection.name)


class FakeAgentLLMClient:
    """A stand-in for `LLMClient` covering everything `src.agents` calls.

    Chat responses are looked up by schema class (configure via
    `chat_responses[Schema] = instance`); embeddings are looked up by
    exact text, falling back to a deterministic hash-based vector so
    tests only need to pin the vectors that matter to their assertions.
    Shared at the root so both `tests/agents/` and `tests/api/` can use it.
    """

    def __init__(self) -> None:
        self.chat_responses: dict[type, object] = {}
        self.embeddings: dict[str, list[float]] = {}
        self.embed_calls: list[list[str]] = []
        self.chat_calls: list[type] = []

    def _fallback_embedding(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode()).digest()
        return [byte / 255 for byte in digest[:8]]

    async def embed(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        self.embed_calls.append(texts)
        return [self.embeddings.get(text, self._fallback_embedding(text)) for text in texts]

    async def chat_json(self, messages: list[dict[str, str]], schema: type, model: str | None = None):
        self.chat_calls.append(schema)
        if schema not in self.chat_responses:
            raise AssertionError(f"No fake response configured for {schema.__name__}")
        return self.chat_responses[schema]


@pytest.fixture
def fake_agent_llm() -> FakeAgentLLMClient:
    return FakeAgentLLMClient()
