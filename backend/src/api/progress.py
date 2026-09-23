import uuid

from fastapi import APIRouter
from pydantic import BaseModel

from src.api.deps import CurrentStudent
from src.core.errors import ForbiddenError
from src.db.session import DbSession
from src.domain import progress as progress_domain

router = APIRouter(prefix="/progress", tags=["progress"])


class TopicProgressOut(BaseModel):
    topic_id: uuid.UUID
    topic_name: str
    document_id: uuid.UUID
    mastery_score: float
    consecutive_failures: int


class ProgressResponse(BaseModel):
    student_id: uuid.UUID
    topics: list[TopicProgressOut]


@router.get("/{student_id}", response_model=ProgressResponse)
async def get_progress(student_id: uuid.UUID, db: DbSession, student: CurrentStudent) -> ProgressResponse:
    """Mastery across every topic the student has ingested material for.

    `student_id` must match the authenticated student — the path param
    exists for a stable, RESTful resource URL, not as an ownership
    override (see `CLAUDE.md` → per-student query scoping).
    """
    if student_id != student.id:
        raise ForbiddenError("Cannot view another student's progress")

    rows = await progress_domain.list_for_student(db, student.id)
    return ProgressResponse(
        student_id=student.id,
        topics=[
            TopicProgressOut(
                topic_id=row.topic_id,
                topic_name=row.topic_name,
                document_id=row.document_id,
                mastery_score=row.mastery_score,
                consecutive_failures=row.consecutive_failures,
            )
            for row in rows
        ],
    )
