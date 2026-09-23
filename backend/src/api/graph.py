import uuid

from fastapi import APIRouter
from pydantic import BaseModel

from src.api.deps import CurrentStudent
from src.db.session import DbSession
from src.domain import topics as topics_domain

router = APIRouter(prefix="/graph", tags=["graph"])


class SubtopicOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    position: int


class TopicNodeOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    position: int
    mastery_score: float
    subtopics: list[SubtopicOut]
    prerequisite_ids: list[uuid.UUID]


class CourseGraphResponse(BaseModel):
    course_id: uuid.UUID
    topics: list[TopicNodeOut]


@router.get("/{course_id}", response_model=CourseGraphResponse)
async def get_course_graph(
    course_id: uuid.UUID, db: DbSession, student: CurrentStudent
) -> CourseGraphResponse:
    """The full topic graph for one document ("course"): nodes, subtopics, prerequisite edges, mastery."""
    nodes = await topics_domain.get_course_graph(db, student.id, course_id)

    return CourseGraphResponse(
        course_id=course_id,
        topics=[
            TopicNodeOut(
                id=node.topic.id,
                name=node.topic.name,
                description=node.topic.description,
                position=node.topic.position,
                mastery_score=node.mastery_score,
                subtopics=[
                    SubtopicOut(
                        id=subtopic.id,
                        name=subtopic.name,
                        description=subtopic.description,
                        position=subtopic.position,
                    )
                    for subtopic in node.subtopics
                ],
                prerequisite_ids=node.prerequisite_ids,
            )
            for node in nodes
        ],
    )
