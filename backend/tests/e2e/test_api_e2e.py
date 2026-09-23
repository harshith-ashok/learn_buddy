import base64
import json
import uuid

import httpx
import pytest

from tests.e2e.conftest import auth_headers, register_student

pytestmark = pytest.mark.e2e


async def test_health(client: httpx.AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_register_then_access_a_protected_route(client: httpx.AsyncClient) -> None:
    tokens = await register_student(client)

    response = await client.get("/documents", headers=auth_headers(tokens))

    assert response.status_code == 200
    assert response.json() == []


async def test_protected_route_without_a_token_is_unauthorized(client: httpx.AsyncClient) -> None:
    response = await client.get("/documents")

    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


async def test_duplicate_registration_is_a_conflict(client: httpx.AsyncClient) -> None:
    email = f"{uuid.uuid4().hex}@example.com"
    payload = {"email": email, "password": "correct-horse-battery-staple", "full_name": "Dup"}

    first = await client.post("/auth/register", json=payload)
    second = await client.post("/auth/register", json=payload)

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["code"] == "conflict"


async def test_login_with_wrong_password_is_unauthorized(client: httpx.AsyncClient) -> None:
    email = f"{uuid.uuid4().hex}@example.com"
    await client.post(
        "/auth/register", json={"email": email, "password": "correct-horse-battery-staple", "full_name": "L"}
    )

    response = await client.post("/auth/login", json={"email": email, "password": "wrong-password"})

    assert response.status_code == 401


async def test_refresh_rotates_the_token_and_rejects_reuse(client: httpx.AsyncClient) -> None:
    tokens = await register_student(client)

    refreshed = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    assert refreshed.json()["refresh_token"] != tokens["refresh_token"]

    reused = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reused.status_code == 401


async def test_progress_for_another_student_is_forbidden(client: httpx.AsyncClient) -> None:
    student_a = await register_student(client)
    student_b_response = await client.post(
        "/auth/register",
        json={
            "email": f"{uuid.uuid4().hex}@example.com",
            "password": "correct-horse-battery-staple",
            "full_name": "B",
        },
    )
    student_b_id = _decode_student_id(student_b_response.json())

    response = await client.get(f"/progress/{student_b_id}", headers=auth_headers(student_a))

    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"


async def test_recommendation_next_with_no_material_returns_no_recommendation(
    client: httpx.AsyncClient,
) -> None:
    tokens = await register_student(client)

    response = await client.get("/recommendation/next", headers=auth_headers(tokens))

    assert response.status_code == 200
    body = response.json()
    assert "reason" in body
    assert "topic_id" not in body


def _decode_student_id(tokens: dict) -> str:
    """Pull `sub` out of the access token's JWT payload without a JWT library.

    The e2e image doesn't need `pyjwt`'s secret-verified decode — the
    token was just issued by the server we're testing, over a connection
    we trust for the test — this only needs to read the claim back out.
    """
    _, payload_b64, _ = tokens["access_token"].split(".")
    padded = payload_b64 + "=" * (-len(payload_b64) % 4)
    payload = json.loads(base64.urlsafe_b64decode(padded))
    return payload["sub"]
