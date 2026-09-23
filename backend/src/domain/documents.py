import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.errors import NotFoundError
from src.db.models import Document, DocumentStatus


async def find_by_content_hash(db: AsyncSession, student_id: uuid.UUID, content_hash: str) -> Document | None:
    return await db.scalar(
        select(Document).where(Document.student_id == student_id, Document.content_hash == content_hash)
    )


async def get_for_student(db: AsyncSession, student_id: uuid.UUID, document_id: uuid.UUID) -> Document:
    document = await db.scalar(
        select(Document).where(Document.id == document_id, Document.student_id == student_id)
    )
    if document is None:
        raise NotFoundError("Document not found")
    return document


async def list_for_student(db: AsyncSession, student_id: uuid.UUID) -> list[Document]:
    result = await db.scalars(
        select(Document).where(Document.student_id == student_id).order_by(Document.created_at.desc())
    )
    return list(result)


async def create_or_replace(
    db: AsyncSession,
    student_id: uuid.UUID,
    filename: str,
    content_hash: str,
    storage_path: str,
    exam_date: datetime | None = None,
) -> tuple[Document, bool]:
    """Get-or-create by `(student_id, content_hash)` — the idempotent-reupload path.

    An identical re-upload (same bytes) reuses the existing `documents`
    row, reset to `PENDING` for reprocessing, rather than creating a
    duplicate. Returns `(document, created)`.
    """
    existing = await find_by_content_hash(db, student_id, content_hash)
    if existing is not None:
        existing.filename = filename
        existing.storage_path = storage_path
        existing.status = DocumentStatus.PENDING
        if exam_date is not None:
            existing.exam_date = exam_date
        await db.flush()
        return existing, False

    document = Document(
        student_id=student_id,
        filename=filename,
        storage_path=storage_path,
        content_hash=content_hash,
        status=DocumentStatus.PENDING,
        exam_date=exam_date,
    )
    db.add(document)
    await db.flush()
    return document, True
