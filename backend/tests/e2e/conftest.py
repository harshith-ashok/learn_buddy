import os
import uuid
from collections.abc import AsyncGenerator

import httpx
import pytest_asyncio

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[httpx.AsyncClient]:
    """A real HTTP client against `BACKEND_URL` — no ASGI transport, no in-process app.

    These tests exercise the actual running `backend` container (see
    `docker-compose.yml`'s `backend-tests` service, `test` profile), not
    the app object — the point is to catch anything Docker networking,
    real uvicorn, or a missing env var in the container would break that
    an in-process `ASGITransport` client (`tests/api/`) can't see.
    """
    async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=30.0) as async_client:
        yield async_client


async def register_student(client: httpx.AsyncClient) -> dict:
    """Register a fresh, uniquely-emailed student and return its token pair."""
    response = await client.post(
        "/auth/register",
        json={
            "email": f"{uuid.uuid4().hex}@example.com",
            "password": "correct-horse-battery-staple",
            "full_name": "E2E Student",
        },
    )
    response.raise_for_status()
    return response.json()


def auth_headers(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}
