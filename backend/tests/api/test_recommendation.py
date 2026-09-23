from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import create_access_token, hash_password
from src.db.models import Student


async def test_recommendation_next_with_no_material_returns_a_reason(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    student = Student(email="rec1@example.com", hashed_password=hash_password("x"), full_name="R")
    db_session.add(student)
    await db_session.flush()
    token = create_access_token(str(student.id))

    response = await client.get("/recommendation/next", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert "reason" in body
    assert "topic_id" not in body
