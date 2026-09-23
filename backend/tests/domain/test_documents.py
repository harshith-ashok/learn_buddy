import uuid
from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.errors import NotFoundError
from src.core.security import hash_password
from src.db.models import DocumentStatus, Student
from src.domain import documents as documents_domain


async def _make_student(db_session: AsyncSession) -> Student:
    student = Student(
        email=f"{uuid.uuid4().hex}@example.com", hashed_password=hash_password("x"), full_name="D"
    )
    db_session.add(student)
    await db_session.flush()
    return student


async def test_create_or_replace_creates_a_new_document_with_exam_date(db_session: AsyncSession) -> None:
    student = await _make_student(db_session)
    exam_date = datetime(2026, 5, 1)

    document, created = await documents_domain.create_or_replace(
        db_session,
        student_id=student.id,
        filename="notes.pdf",
        content_hash="abc123",
        storage_path="/tmp/notes.pdf",
        exam_date=exam_date,
    )

    assert created is True
    assert document.status == DocumentStatus.PENDING
    assert document.exam_date == exam_date


async def test_create_or_replace_reuses_the_existing_row_for_identical_bytes(
    db_session: AsyncSession,
) -> None:
    student = await _make_student(db_session)
    first, _ = await documents_domain.create_or_replace(
        db_session,
        student_id=student.id,
        filename="v1.pdf",
        content_hash="same-hash",
        storage_path="/tmp/v1.pdf",
    )

    second, created = await documents_domain.create_or_replace(
        db_session,
        student_id=student.id,
        filename="v2.pdf",
        content_hash="same-hash",
        storage_path="/tmp/v2.pdf",
    )

    assert created is False
    assert second.id == first.id
    assert second.filename == "v2.pdf"
    assert second.status == DocumentStatus.PENDING


async def test_create_or_replace_updates_exam_date_on_reupload_when_given(db_session: AsyncSession) -> None:
    student = await _make_student(db_session)
    original_exam_date = datetime(2026, 5, 1)
    await documents_domain.create_or_replace(
        db_session,
        student_id=student.id,
        filename="notes.pdf",
        content_hash="same-hash",
        storage_path="/tmp/notes.pdf",
        exam_date=original_exam_date,
    )

    updated_exam_date = datetime(2026, 6, 15)
    document, _ = await documents_domain.create_or_replace(
        db_session,
        student_id=student.id,
        filename="notes.pdf",
        content_hash="same-hash",
        storage_path="/tmp/notes.pdf",
        exam_date=updated_exam_date,
    )

    assert document.exam_date == updated_exam_date


async def test_create_or_replace_keeps_exam_date_when_reupload_omits_it(db_session: AsyncSession) -> None:
    student = await _make_student(db_session)
    exam_date = datetime(2026, 5, 1)
    await documents_domain.create_or_replace(
        db_session,
        student_id=student.id,
        filename="notes.pdf",
        content_hash="same-hash",
        storage_path="/tmp/notes.pdf",
        exam_date=exam_date,
    )

    document, _ = await documents_domain.create_or_replace(
        db_session,
        student_id=student.id,
        filename="notes.pdf",
        content_hash="same-hash",
        storage_path="/tmp/notes.pdf",
    )

    assert document.exam_date == exam_date


async def test_get_for_student_raises_not_found_for_a_foreign_document(db_session: AsyncSession) -> None:
    student = await _make_student(db_session)
    with pytest.raises(NotFoundError):
        await documents_domain.get_for_student(db_session, student.id, uuid.uuid4())


async def test_list_for_student_orders_newest_first(db_session: AsyncSession) -> None:
    # Postgres' now() is the transaction's start time, not per-statement —
    # both inserts in this test's single transaction would otherwise tie,
    # so the timestamps are set explicitly to make the ordering meaningful.
    student = await _make_student(db_session)
    older, _ = await documents_domain.create_or_replace(
        db_session, student_id=student.id, filename="a.pdf", content_hash="a", storage_path="/tmp/a.pdf"
    )
    older.created_at = datetime(2020, 1, 1)
    newer, _ = await documents_domain.create_or_replace(
        db_session, student_id=student.id, filename="b.pdf", content_hash="b", storage_path="/tmp/b.pdf"
    )
    newer.created_at = datetime(2024, 1, 1)
    await db_session.flush()

    documents = await documents_domain.list_for_student(db_session, student.id)

    assert [document.id for document in documents] == [newer.id, older.id]
