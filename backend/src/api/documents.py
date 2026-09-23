import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, File, Form, UploadFile
from pydantic import BaseModel

from src.api.deps import CurrentStudent, LLMClientDep, VectorStoreDep
from src.core.config import get_settings
from src.core.errors import AppError
from src.db.models import DocumentStatus
from src.db.session import DbSession, SessionFactoryDep
from src.domain import documents as documents_domain
from src.ingestion import storage
from src.ingestion.parsers import SUPPORTED_EXTENSIONS, UnsupportedDocumentFormatError
from src.ingestion.pipeline import process_document

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentUploadResponse(BaseModel):
    id: uuid.UUID
    filename: str
    status: DocumentStatus
    created: bool


class PayloadTooLargeError(AppError):
    def __init__(self, max_mb: int) -> None:
        super().__init__(
            code="payload_too_large",
            message=f"File exceeds the {max_mb}MB upload limit",
            status_code=413,
        )


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    db: DbSession,
    student: CurrentStudent,
    llm_client: LLMClientDep,
    vectorstore: VectorStoreDep,
    session_factory: SessionFactoryDep,
    file: Annotated[UploadFile, File()],
    exam_date: Annotated[datetime | None, Form()] = None,
) -> DocumentUploadResponse:
    """Accept a syllabus/notes file, store it, and enqueue ingestion.

    Re-uploading identical bytes (same content hash) reuses the existing
    `documents` row instead of creating a duplicate — see
    `domain.documents.create_or_replace`.
    """
    settings = get_settings()
    filename = file.filename or "upload"
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise UnsupportedDocumentFormatError(filename)

    content = await file.read()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise PayloadTooLargeError(settings.max_upload_size_mb)

    content_hash = storage.compute_content_hash(content)
    path = storage.storage_path(str(student.id), content_hash, extension, settings)
    await storage.save_file(content, path)

    document, created = await documents_domain.create_or_replace(
        db,
        student_id=student.id,
        filename=filename,
        content_hash=content_hash,
        storage_path=str(path),
        exam_date=exam_date,
    )
    await db.commit()

    background_tasks.add_task(process_document, document.id, llm_client, vectorstore, session_factory)

    return DocumentUploadResponse(
        id=document.id, filename=document.filename, status=document.status, created=created
    )


class DocumentOut(BaseModel):
    id: uuid.UUID
    filename: str
    status: DocumentStatus
    exam_date: datetime | None


@router.get("", response_model=list[DocumentOut])
async def list_documents(db: DbSession, student: CurrentStudent) -> list[DocumentOut]:
    documents = await documents_domain.list_for_student(db, student.id)
    return [
        DocumentOut(id=doc.id, filename=doc.filename, status=doc.status, exam_date=doc.exam_date)
        for doc in documents
    ]


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(document_id: uuid.UUID, db: DbSession, student: CurrentStudent) -> DocumentOut:
    document = await documents_domain.get_for_student(db, student.id, document_id)
    return DocumentOut(
        id=document.id, filename=document.filename, status=document.status, exam_date=document.exam_date
    )
