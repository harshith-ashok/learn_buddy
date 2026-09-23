import uuid

from httpx import AsyncClient
from sqlalchemy import select

from src.db.models import Student


def _register_payload(email: str | None = None) -> dict:
    return {
        "email": email or f"{uuid.uuid4().hex}@example.com",
        "password": "correct-horse-battery-staple",
        "full_name": "Auth Test",
    }


async def test_register_creates_a_student_and_returns_tokens(client: AsyncClient, db_session) -> None:
    payload = _register_payload()

    response = await client.post("/auth/register", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["access_token"] and body["refresh_token"]

    student = await db_session.scalar(select(Student).where(Student.email == payload["email"]))
    assert student is not None


async def test_register_duplicate_email_is_a_conflict(client: AsyncClient) -> None:
    payload = _register_payload()

    first = await client.post("/auth/register", json=payload)
    second = await client.post("/auth/register", json=payload)

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["code"] == "conflict"


async def test_login_with_correct_credentials_returns_tokens(client: AsyncClient) -> None:
    payload = _register_payload()
    await client.post("/auth/register", json=payload)

    response = await client.post(
        "/auth/login", json={"email": payload["email"], "password": payload["password"]}
    )

    assert response.status_code == 200
    assert response.json()["access_token"]


async def test_login_with_wrong_password_is_unauthorized(client: AsyncClient) -> None:
    payload = _register_payload()
    await client.post("/auth/register", json=payload)

    response = await client.post("/auth/login", json={"email": payload["email"], "password": "wrong"})

    assert response.status_code == 401


async def test_login_with_unknown_email_is_unauthorized(client: AsyncClient) -> None:
    response = await client.post("/auth/login", json={"email": "nobody@example.com", "password": "x"})

    assert response.status_code == 401


async def test_refresh_rotates_and_rejects_reuse(client: AsyncClient) -> None:
    tokens = (await client.post("/auth/register", json=_register_payload())).json()

    refreshed = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    new_tokens = refreshed.json()
    assert new_tokens["refresh_token"] != tokens["refresh_token"]

    reused = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reused.status_code == 401

    still_good = await client.post("/auth/refresh", json={"refresh_token": new_tokens["refresh_token"]})
    assert still_good.status_code == 200


async def test_logout_revokes_the_refresh_token(client: AsyncClient) -> None:
    tokens = (await client.post("/auth/register", json=_register_payload())).json()

    logout_response = await client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert logout_response.status_code == 204

    reused = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reused.status_code == 401


async def test_access_token_reaches_a_protected_route(client: AsyncClient) -> None:
    tokens = (await client.post("/auth/register", json=_register_payload())).json()

    response = await client.get("/documents", headers={"Authorization": f"Bearer {tokens['access_token']}"})

    assert response.status_code == 200
    assert response.json() == []


async def test_missing_token_is_unauthorized(client: AsyncClient) -> None:
    response = await client.get("/documents")

    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"
