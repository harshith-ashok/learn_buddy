import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.agents.chat import answer_topic_question
from src.api.deps import CurrentStudent, LLMClientDep, VectorStoreDep, rate_limiter
from src.core.config import get_settings
from src.db.models import ChatMessage, ChatMessageRole
from src.db.session import DbSession
from src.domain import chat as chat_domain
from src.domain import topics as topics_domain

_settings = get_settings()

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
    dependencies=[
        Depends(
            rate_limiter(
                "chat_ask", _settings.chat_ask_rate_limit, _settings.chat_ask_rate_limit_window_seconds
            )
        )
    ],
)


class AskRequest(BaseModel):
    topic_id: uuid.UUID
    message: str = Field(min_length=1, max_length=2000)


class RelatedTopicOut(BaseModel):
    topic_id: uuid.UUID
    topic_name: str


class ChatMessageOut(BaseModel):
    id: uuid.UUID
    topic_id: uuid.UUID
    role: ChatMessageRole
    content: str
    source_chunk_ids: list[str]
    related_topics: list[RelatedTopicOut]
    covered: bool


def _to_out(message: ChatMessage, topic_names: dict[uuid.UUID, str]) -> ChatMessageOut:
    related_topics = [
        RelatedTopicOut(topic_id=related_id, topic_name=topic_names[related_id])
        for related_id in (uuid.UUID(rid) for rid in message.related_topic_ids)
        # A related topic could since have been deleted (document removed,
        # re-upload replaced its topics) — skip rather than 500 on a stale id.
        if related_id in topic_names
    ]
    return ChatMessageOut(
        id=message.id,
        topic_id=message.topic_id,
        role=message.role,
        content=message.content,
        source_chunk_ids=message.source_chunk_ids,
        related_topics=related_topics,
        # A user turn has no "coverage" of its own; an assistant turn was
        # grounded (has citations) unless it's the fixed refusal text —
        # cheaper than a dedicated column for something the frontend only
        # uses to pick a bubble style.
        covered=message.role == ChatMessageRole.ASSISTANT
        and (bool(message.source_chunk_ids) or bool(related_topics)),
    )


@router.post("/ask", response_model=ChatMessageOut)
async def ask(
    payload: AskRequest,
    db: DbSession,
    student: CurrentStudent,
    llm_client: LLMClientDep,
    vectorstore: VectorStoreDep,
) -> ChatMessageOut:
    """Ask a question about one topic, grounded strictly in that topic's own document.

    Rate-limited (`chat_ask_rate_limit` per `chat_ask_rate_limit_window_seconds`)
    — this calls the model, same as study-kit generation. Persists both the
    student's question and the assistant's answer (or refusal) as
    `chat_messages` rows, so `GET /chat` replays the same transcript.
    """
    await chat_domain.add_message(db, student.id, payload.topic_id, ChatMessageRole.USER, payload.message)

    result = await answer_topic_question(
        db, student.id, payload.topic_id, payload.message, llm_client, vectorstore
    )

    assistant_message = await chat_domain.add_message(
        db,
        student.id,
        payload.topic_id,
        ChatMessageRole.ASSISTANT,
        result.answer,
        source_chunk_ids=result.source_chunk_ids,
        related_topic_ids=[related.topic_id for related in result.related_topics],
    )
    await db.commit()
    topic_names = {related.topic_id: related.topic_name for related in result.related_topics}
    return _to_out(assistant_message, topic_names)


@router.get("", response_model=list[ChatMessageOut])
async def list_messages(topic_id: uuid.UUID, db: DbSession, student: CurrentStudent) -> list[ChatMessageOut]:
    """The full chat transcript for `topic_id`, oldest first."""
    messages = await chat_domain.list_for_topic(db, student.id, topic_id)
    all_related_ids = {uuid.UUID(rid) for message in messages for rid in message.related_topic_ids}
    topic_names = await topics_domain.get_names(db, all_related_ids)
    return [_to_out(message, topic_names) for message in messages]
