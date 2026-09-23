import asyncio
import json
from functools import lru_cache
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from src.core.config import Settings, get_settings
from src.core.errors import LLMError
from src.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)

_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def _strip_markdown_fence(content: str) -> str:
    """Undo a ```json ... ``` wrapper some models add despite a JSON-only response format.

    This is a formatting correction, not a free-text parse: it doesn't try
    to extract or interpret meaning from the content, only strips a
    literal fence around what's still expected to be nothing but JSON
    (validated by Pydantic right after this runs).
    """
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = stripped.removeprefix("```json").removeprefix("```")
        stripped = stripped.removesuffix("```")
        stripped = stripped.strip()
    return stripped


def _auth_headers(settings: Settings) -> dict[str, str]:
    # No Authorization header at all when there's no key (e.g. a local
    # Ollama instance) — "Bearer " with nothing after it is an empty,
    # trailing-whitespace header value, which httpx/h11 reject outright
    # when the request is actually sent.
    return {"Authorization": f"Bearer {settings.ollama_api_key}"} if settings.ollama_api_key else {}


class LLMClient:
    """The one place every Ollama Cloud call goes through.

    Owns the HTTP client, auth header, retries, timeouts, and error
    translation — per `CLAUDE.md` → "Model configuration". Chat calls use
    JSON-schema-constrained structured output, validated with Pydantic on
    receipt; nothing parses free-text model output.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = httpx.AsyncClient(
            base_url=settings.ollama_base_url,
            headers=_auth_headers(settings),
            timeout=settings.ollama_timeout_seconds,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _post_with_retry(self, path: str, json_body: dict[str, Any]) -> dict[str, Any]:
        last_error: Exception | None = None

        for attempt in range(self._settings.ollama_max_retries):
            try:
                response = await self._client.post(path, json=json_body)
                if response.status_code in _RETRYABLE_STATUS_CODES:
                    last_error = LLMError(
                        f"Ollama returned {response.status_code}", {"body": response.text[:500]}
                    )
                elif response.is_error:
                    raise LLMError(f"Ollama returned {response.status_code}", {"body": response.text[:500]})
                else:
                    return response.json()
            except httpx.TransportError as exc:
                last_error = LLMError(f"Ollama request failed: {exc}")

            if attempt < self._settings.ollama_max_retries - 1:
                backoff = 0.5 * (2**attempt)
                logger.warning(
                    "Retrying Ollama call",
                    extra={"path": path, "attempt": attempt + 1, "backoff_seconds": backoff},
                )
                await asyncio.sleep(backoff)

        assert last_error is not None
        raise last_error

    async def embed(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        """Embed `texts`, preserving input order."""
        if not texts:
            return []

        body = await self._post_with_retry(
            "/v1/embeddings",
            {"model": model or self._settings.ollama_embed_model, "input": texts},
        )
        try:
            data = sorted(body["data"], key=lambda item: item["index"])
            return [item["embedding"] for item in data]
        except (KeyError, TypeError) as exc:
            raise LLMError("Malformed embeddings response", {"body": str(body)[:500]}) from exc

    async def chat_json(
        self,
        messages: list[dict[str, str]],
        schema: type[T],
        model: str | None = None,
    ) -> T:
        """Call chat completions constrained to `schema`, and validate the result.

        Raises `LLMError` on any failure — transport, non-2xx, or a
        response that doesn't validate against `schema`. Never falls back
        to parsing free text.

        Uses `response_format: json_object` rather than `json_schema`: the
        served `gpt-oss:120b-cloud` build ignores `json_schema`'s `strict`
        constraint and returns markdown prose instead (verified against
        this deployment), so the exact shape is instead spelled out as a
        system message and enforced by the Pydantic validation below.
        """
        schema_instruction = {
            "role": "system",
            "content": (
                "Respond with a single raw JSON object only — no markdown "
                "fences, no prose before or after it. It must validate "
                f"against this JSON Schema:\n{json.dumps(schema.model_json_schema())}"
            ),
        }
        body = await self._post_with_retry(
            "/v1/chat/completions",
            {
                "model": model or self._settings.ollama_model,
                "messages": [*messages, schema_instruction],
                "response_format": {"type": "json_object"},
            },
        )
        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("Malformed chat completion response", {"body": str(body)[:500]}) from exc

        try:
            return schema.model_validate(json.loads(_strip_markdown_fence(content)))
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.error("Model output failed schema validation", extra={"schema": schema.__name__})
            raise LLMError(
                f"Model output did not match {schema.__name__}", {"content": content[:500]}
            ) from exc


@lru_cache
def get_llm_client() -> LLMClient:
    return LLMClient(get_settings())
