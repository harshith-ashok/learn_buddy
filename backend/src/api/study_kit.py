import uuid

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from src.agents.schemas import NotCovered
from src.agents.study_kit import CONTENT_SCHEMA_BY_KIT_TYPE, generate_study_kit, persist_study_kit
from src.api.deps import CurrentStudent, LLMClientDep, VectorStoreDep, rate_limiter
from src.core.config import get_settings
from src.db.models import StudyKit, StudyKitType
from src.db.session import DbSession
from src.domain import study_kits as study_kits_domain

_settings = get_settings()

router = APIRouter(
    prefix="/study-kit",
    tags=["study-kit"],
    dependencies=[
        Depends(
            rate_limiter(
                "study_kit_generate",
                _settings.study_kit_generation_rate_limit,
                _settings.study_kit_generation_rate_limit_window_seconds,
            )
        )
    ],
)


class GenerateStudyKitRequest(BaseModel):
    topic_id: uuid.UUID
    kit_type: StudyKitType


class StudyKitOut(BaseModel):
    id: uuid.UUID
    topic_id: uuid.UUID
    kit_type: StudyKitType
    content: dict
    source_chunk_ids: list[str]


def _redact_quiz_answers(kit_type: StudyKitType, content: dict) -> dict:
    """Strip `correct_index` from quiz content before it ever reaches a client.

    `POST /quiz/submit` grades against the DB row directly
    (`agents.quiz_grading`), never against what this API returned, so
    withholding it here costs nothing and closes an obvious "read the
    network tab" cheat — see `wiki/decisions/0007-server-side-quiz-grading.md`.
    """
    if kit_type != StudyKitType.QUIZ:
        return content
    return {
        **content,
        "questions": [
            {key: value for key, value in question.items() if key != "correct_index"}
            for question in content.get("questions", [])
        ],
    }


def _normalize_content(kit_type: StudyKitType, content: dict) -> dict:
    """Backfill defaults for any schema field added since a row was generated.

    `content` is stored as bare JSON with no schema versioning — a row
    generated before `formulas` existed on `SummaryContent`/`ProblemGuideContent`
    simply has no `formulas` key. Re-validating through the same schema
    `generate_study_kit` used and dumping it back out fills in that
    field's default (`[]`) instead of the frontend reading `undefined`
    for a field its types declare as always present.
    """
    schema = CONTENT_SCHEMA_BY_KIT_TYPE[kit_type]
    return schema.model_validate(content).model_dump(mode="json")


def _to_out(study_kit: StudyKit) -> StudyKitOut:
    content = _normalize_content(study_kit.kit_type, study_kit.content)
    return StudyKitOut(
        id=study_kit.id,
        topic_id=study_kit.topic_id,
        kit_type=study_kit.kit_type,
        content=_redact_quiz_answers(study_kit.kit_type, content),
        source_chunk_ids=study_kit.source_chunk_ids,
    )


@router.post("/generate", response_model=StudyKitOut | NotCovered, status_code=status.HTTP_201_CREATED)
async def generate(
    payload: GenerateStudyKitRequest,
    db: DbSession,
    student: CurrentStudent,
    llm_client: LLMClientDep,
    vectorstore: VectorStoreDep,
) -> StudyKitOut | NotCovered:
    """Generate and persist a study kit, grounded in the student's own material.

    Rate-limited (`study_kit_generation_rate_limit` per
    `study_kit_generation_rate_limit_window_seconds`) — the only route in
    this API that calls the model to generate new content, per `TODO.md`
    → "Rate limiting via the Redis wrapper on generation endpoints".
    Returns `NotCovered` (200-shaped, not an error) when nothing in the
    student's material clears the retrieval guardrail.
    """
    result = await generate_study_kit(
        db, student.id, payload.topic_id, payload.kit_type, llm_client, vectorstore
    )
    if isinstance(result, NotCovered):
        return result

    study_kit = await persist_study_kit(db, student.id, payload.topic_id, result)
    await db.commit()
    return _to_out(study_kit)


@router.get("", response_model=list[StudyKitOut])
async def list_study_kits(topic_id: uuid.UUID, db: DbSession, student: CurrentStudent) -> list[StudyKitOut]:
    """Every study kit already generated for `topic_id`, newest first."""
    kits = await study_kits_domain.list_for_topic(db, student.id, topic_id)
    return [_to_out(kit) for kit in kits]


@router.get("/{study_kit_id}", response_model=StudyKitOut)
async def get_study_kit(study_kit_id: uuid.UUID, db: DbSession, student: CurrentStudent) -> StudyKitOut:
    study_kit = await study_kits_domain.get_for_student(db, student.id, study_kit_id)
    return _to_out(study_kit)
