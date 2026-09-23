import json

import httpx
import pytest
from pydantic import BaseModel

from src.core.config import Settings
from src.core.errors import LLMError
from src.core.llm_client import LLMClient, _auth_headers, _strip_markdown_fence


class _Widget(BaseModel):
    name: str
    count: int


@pytest.fixture(autouse=True)
def _no_real_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    async def instant_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr("src.core.llm_client.asyncio.sleep", instant_sleep)


def _client(handler: httpx.MockTransport, **overrides) -> LLMClient:
    settings = Settings(ollama_base_url="https://fake-ollama.test", ollama_max_retries=2, **overrides)
    client = LLMClient(settings)
    client._client = httpx.AsyncClient(
        base_url=settings.ollama_base_url,
        headers=_auth_headers(settings),
        transport=handler,
        timeout=settings.ollama_timeout_seconds,
    )
    return client


async def test_embed_returns_vectors_in_request_order() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": 1, "embedding": [0.2, 0.2]},
                    {"index": 0, "embedding": [0.1, 0.1]},
                ]
            },
        )

    client = _client(httpx.MockTransport(handler))
    try:
        result = await client.embed(["a", "b"])
    finally:
        await client.aclose()

    assert result == [[0.1, 0.1], [0.2, 0.2]]


async def test_embed_empty_input_short_circuits_without_a_call() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("should not be called for empty input")

    client = _client(httpx.MockTransport(handler))
    try:
        assert await client.embed([]) == []
    finally:
        await client.aclose()


async def test_chat_json_validates_structured_output() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps({"name": "gizmo", "count": 3})}}]},
        )

    client = _client(httpx.MockTransport(handler))
    try:
        result = await client.chat_json([{"role": "user", "content": "hi"}], _Widget)
    finally:
        await client.aclose()

    assert result == _Widget(name="gizmo", count=3)


async def test_chat_json_strips_markdown_fence_around_json() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        fenced = "```json\n" + json.dumps({"name": "gizmo", "count": 3}) + "\n```"
        return httpx.Response(200, json={"choices": [{"message": {"content": fenced}}]})

    client = _client(httpx.MockTransport(handler))
    try:
        result = await client.chat_json([{"role": "user", "content": "hi"}], _Widget)
    finally:
        await client.aclose()

    assert result == _Widget(name="gizmo", count=3)


async def test_chat_json_raises_llm_error_on_schema_mismatch() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps({"name": "gizmo"})}}]},  # missing "count"
        )

    client = _client(httpx.MockTransport(handler))
    try:
        with pytest.raises(LLMError):
            await client.chat_json([{"role": "user", "content": "hi"}], _Widget)
    finally:
        await client.aclose()


async def test_retries_on_5xx_then_succeeds() -> None:
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        if attempts["n"] < 2:
            return httpx.Response(503, text="unavailable")
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps({"name": "gizmo", "count": 1})}}]},
        )

    client = _client(httpx.MockTransport(handler))
    try:
        result = await client.chat_json([{"role": "user", "content": "hi"}], _Widget)
    finally:
        await client.aclose()

    assert attempts["n"] == 2
    assert result.count == 1


async def test_exhausts_retries_and_raises_llm_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    client = _client(httpx.MockTransport(handler))
    try:
        with pytest.raises(LLMError):
            await client.chat_json([{"role": "user", "content": "hi"}], _Widget)
    finally:
        await client.aclose()


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ('{"a": 1}', '{"a": 1}'),
        ('```json\n{"a": 1}\n```', '{"a": 1}'),
        ('```\n{"a": 1}\n```', '{"a": 1}'),
        ('  \n```json\n{"a": 1}\n```\n  ', '{"a": 1}'),
    ],
)
def test_strip_markdown_fence(raw: str, expected: str) -> None:
    assert _strip_markdown_fence(raw) == expected


async def test_no_api_key_omits_authorization_header() -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["has_auth"] = "authorization" in request.headers
        return httpx.Response(200, json={"data": [{"index": 0, "embedding": [0.1]}]})

    client = _client(httpx.MockTransport(handler), ollama_api_key="")
    try:
        await client.embed(["a"])
    finally:
        await client.aclose()

    assert captured["has_auth"] is False


async def test_4xx_raises_immediately_without_retry() -> None:
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        return httpx.Response(400, text="bad request")

    client = _client(httpx.MockTransport(handler))
    try:
        with pytest.raises(LLMError):
            await client.chat_json([{"role": "user", "content": "hi"}], _Widget)
    finally:
        await client.aclose()

    assert attempts["n"] == 1
