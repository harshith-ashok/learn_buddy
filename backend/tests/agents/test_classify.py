from src.agents.classify import classify_intent
from src.agents.schemas import Intent, IntentClassification
from src.core.errors import LLMError


async def test_classify_intent_returns_validated_classification(fake_agent_llm) -> None:
    fake_agent_llm.chat_responses[IntentClassification] = IntentClassification(
        intent=Intent.RECOMMEND_NEXT, confidence=0.9
    )

    result = await classify_intent("what should I study next?", fake_agent_llm)

    assert result.intent is Intent.RECOMMEND_NEXT
    assert fake_agent_llm.chat_calls == [IntentClassification]


async def test_classify_intent_falls_back_to_other_on_llm_error(fake_agent_llm, monkeypatch) -> None:
    async def _raise(*args, **kwargs):
        raise LLMError("bad output")

    monkeypatch.setattr(fake_agent_llm, "chat_json", _raise)

    result = await classify_intent("asdf jkl;", fake_agent_llm)

    assert result.intent is Intent.OTHER
    assert result.confidence == 0.0
