from fastapi import APIRouter

from src.agents.recommend import recommend_next_topic
from src.agents.schemas import NoRecommendation, Recommendation
from src.api.deps import CurrentStudent
from src.db.session import DbSession

router = APIRouter(prefix="/recommendation", tags=["recommendation"])


@router.get("/next", response_model=Recommendation | NoRecommendation)
async def get_next_recommendation(
    db: DbSession, student: CurrentStudent
) -> Recommendation | NoRecommendation:
    """The next topic to study, or why there isn't one — see `agents.recommend`."""
    return await recommend_next_topic(db, student.id)
