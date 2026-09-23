from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import hash_password
from src.db.models import Student


async def test_insert_and_fetch_student(db_session: AsyncSession) -> None:
    student = Student(
        email="ada@example.com",
        hashed_password=hash_password("s3cret!"),
        full_name="Ada Lovelace",
    )
    db_session.add(student)
    await db_session.flush()

    fetched = await db_session.scalar(select(Student).where(Student.email == "ada@example.com"))

    assert fetched is not None
    assert fetched.id == student.id
    assert fetched.full_name == "Ada Lovelace"
    assert fetched.created_at is not None


async def test_email_uniqueness_is_enforced(db_session: AsyncSession) -> None:
    from sqlalchemy.exc import IntegrityError

    db_session.add(Student(email="dup@example.com", hashed_password="x", full_name="One"))
    await db_session.flush()

    db_session.add(Student(email="dup@example.com", hashed_password="x", full_name="Two"))
    try:
        await db_session.flush()
        raise AssertionError("expected IntegrityError for duplicate email")
    except IntegrityError:
        await db_session.rollback()
