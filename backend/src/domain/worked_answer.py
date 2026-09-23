import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import WorkedAnswerAttempt


async def list_for_problem(
    db: AsyncSession, student_id: uuid.UUID, study_kit_id: uuid.UUID, problem_index: int
) -> list[WorkedAnswerAttempt]:
    """Every worked-answer attempt at one problem, scoped to `student_id`, newest first."""
    result = await db.scalars(
        select(WorkedAnswerAttempt)
        .where(
            WorkedAnswerAttempt.student_id == student_id,
            WorkedAnswerAttempt.study_kit_id == study_kit_id,
            WorkedAnswerAttempt.problem_index == problem_index,
        )
        .order_by(WorkedAnswerAttempt.created_at.desc())
    )
    return list(result)
