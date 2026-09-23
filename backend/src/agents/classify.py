from src.agents.schemas import Intent, IntentClassification
from src.core.errors import LLMError
from src.core.llm_client import LLMClient
from src.core.logging import get_logger

logger = get_logger(__name__)

_SYSTEM_PROMPT = (
    "You are an intent classifier for a learning assistant. Classify the student's "
    "message into exactly one of: recommend_next (asking what to study next), "
    "generate_study_kit (asking for a summary, flashcards, quiz, or problem guide on "
    "a topic), submit_quiz (reporting or submitting quiz answers/results), or other "
    "(anything else). Respond with the intent and your confidence in it."
)


async def classify_intent(message: str, llm_client: LLMClient) -> IntentClassification:
    """Classify `message` into a fixed intent enum with one constrained model call.

    A validation failure (malformed JSON, or a schema mismatch already
    caught by `LLMClient.chat_json`) is treated as `other` and logged —
    never silently retried into a guess, per `CLAUDE.md` → "Agent
    classification".
    """
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": message},
    ]
    try:
        result = await llm_client.chat_json(messages, IntentClassification)
    except LLMError:
        logger.warning("Intent classification failed validation; falling back to other")
        return IntentClassification(intent=Intent.OTHER, confidence=0.0)

    logger.info(
        "Classified intent",
        extra={"intent": result.intent.value, "confidence": result.confidence},
    )
    return result
