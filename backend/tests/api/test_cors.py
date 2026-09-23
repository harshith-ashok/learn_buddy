from httpx import AsyncClient


async def test_preflight_allows_a_configured_frontend_origin(client: AsyncClient) -> None:
    """A browser's CORS preflight for a cross-origin frontend must succeed.

    Without CORSMiddleware, every fetch from the Next.js frontend (a
    different origin/port than the API) is silently blocked by the
    browser — this is the regression test for that gap.
    """
    response = await client.options(
        "/auth/login",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


async def test_preflight_rejects_an_unconfigured_origin(client: AsyncClient) -> None:
    response = await client.options(
        "/auth/login",
        headers={
            "Origin": "http://evil.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert "access-control-allow-origin" not in response.headers
