from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel, Field

from src.core.errors import NotFoundError, register_error_handlers


class _Payload(BaseModel):
    secret: str = Field(min_length=8)


def _make_app() -> FastAPI:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/boom/not-found")
    def boom_not_found() -> None:
        raise NotFoundError("Student not found")

    @app.get("/boom/unhandled")
    def boom_unhandled() -> None:
        raise RuntimeError("something broke")

    @app.post("/boom/validation")
    def boom_validation(payload: _Payload) -> None:
        return None

    return app


async def test_app_error_returns_code_message_envelope() -> None:
    transport = ASGITransport(app=_make_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/boom/not-found")

    assert response.status_code == 404
    assert response.json() == {"code": "not_found", "message": "Student not found"}


async def test_unhandled_exception_returns_internal_error_envelope() -> None:
    # Starlette's ServerErrorMiddleware re-raises after sending the response
    # (so real servers can log it); ASGITransport must not re-raise it here
    # too, or the client never sees the response we're asserting on.
    transport = ASGITransport(app=_make_app(), raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/boom/unhandled")

    assert response.status_code == 500
    assert response.json() == {"code": "internal_error", "message": "An unexpected error occurred"}


async def test_validation_error_does_not_echo_the_submitted_value() -> None:
    """A rejected field's raw value (e.g. a too-short password) must never
    come back in the response body — Pydantic includes it by default."""
    transport = ASGITransport(app=_make_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/boom/validation", json={"secret": "short"})

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    error = body["details"]["errors"][0]
    assert "input" not in error


async def test_404_on_unknown_route_returns_envelope() -> None:
    transport = ASGITransport(app=_make_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/does-not-exist")

    assert response.status_code == 404
    assert response.json()["code"] == "http_error"
