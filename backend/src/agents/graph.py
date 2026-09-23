# pyright: reportTypedDictNotRequiredAccess=false, reportArgumentType=false, reportAssignmentType=false
# AgentState is `total=False` by necessity — different LangGraph nodes
# return different partial updates, and a key's presence at a given read
# site is guaranteed by graph structure (which node ran before which),
# not by the TypedDict itself; static analysis can't see that, the
# node-level tests do. LangGraph's own `add_node`/`ainvoke` signatures are
# also broader (`Runnable`-based) than a plain async function needs to be.
import uuid
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.classify import classify_intent
from src.agents.mastery import score_and_update_mastery
from src.agents.recommend import recommend_next_topic
from src.agents.remediation import build_remediation_plan
from src.agents.schemas import Intent, MasteryUpdateResult, NotCovered, QuizSubmission
from src.agents.study_kit import generate_study_kit, persist_study_kit
from src.core.config import Settings, get_settings
from src.core.llm_client import LLMClient
from src.core.logging import get_logger
from src.core.vectorstore import VectorStoreClient
from src.db.models import StudyKitType

logger = get_logger(__name__)


class AgentState(TypedDict, total=False):
    """State threaded through the graph for one request.

    `mastery_result` carries the typed `submit_quiz` outcome into the
    conditional edge that decides whether `trigger_remediation` runs;
    `result` is the JSON-serializable payload the caller ultimately gets
    back.
    """

    message: str
    student_id: uuid.UUID
    topic_id: uuid.UUID | None
    kit_type: StudyKitType | None
    quiz_submission: QuizSubmission | None
    intent: Intent
    mastery_result: MasteryUpdateResult
    result: dict[str, Any]
    error: str


def build_agent_graph(
    db: AsyncSession,
    llm_client: LLMClient,
    vectorstore: VectorStoreClient,
    settings: Settings | None = None,
):
    """Compile the agent graph bound to one request's dependencies.

    Routing is strictly on the classifier's validated `Intent`, never a
    free-form agent decision — see `CLAUDE.md` → "Agent classification".
    Every node logs its own inputs/outputs (via the modules it delegates
    to) for traceability.
    """
    settings = settings or get_settings()

    async def classify_node(state: AgentState) -> AgentState:
        classification = await classify_intent(state["message"], llm_client)
        return {"intent": classification.intent}

    def route_on_intent(state: AgentState) -> str:
        return state["intent"].value

    async def recommend_node(state: AgentState) -> AgentState:
        recommendation = await recommend_next_topic(db, state["student_id"], settings)
        return {"result": recommendation.model_dump(mode="json")}

    async def study_kit_node(state: AgentState) -> AgentState:
        topic_id = state.get("topic_id")
        kit_type = state.get("kit_type")
        if topic_id is None or kit_type is None:
            return {"error": "generate_study_kit requires topic_id and kit_type"}

        generated = await generate_study_kit(
            db, state["student_id"], topic_id, kit_type, llm_client, vectorstore, settings
        )
        if isinstance(generated, NotCovered):
            return {"result": generated.model_dump(mode="json")}

        study_kit = await persist_study_kit(db, state["student_id"], topic_id, generated)
        return {"result": {**generated.model_dump(mode="json"), "study_kit_id": str(study_kit.id)}}

    async def submit_quiz_node(state: AgentState) -> AgentState:
        topic_id = state.get("topic_id")
        submission = state.get("quiz_submission")
        if topic_id is None or submission is None:
            return {"error": "submit_quiz requires topic_id and quiz_submission"}

        mastery_result = await score_and_update_mastery(
            db, state["student_id"], topic_id, submission, settings
        )
        return {"result": mastery_result.model_dump(mode="json"), "mastery_result": mastery_result}

    def route_after_quiz(state: AgentState) -> str:
        mastery_result = state.get("mastery_result")
        return "remediate" if mastery_result is not None and mastery_result.remediation_triggered else "end"

    async def remediation_node(state: AgentState) -> AgentState:
        mastery_result = state["mastery_result"]
        plan = await build_remediation_plan(
            db, state["student_id"], mastery_result.topic_id, mastery_result, settings
        )
        return {"result": {**state["result"], "remediation": plan.model_dump(mode="json")}}

    async def other_node(_: AgentState) -> AgentState:
        return {
            "result": {
                "message": "I can help with a topic recommendation, a study kit, or a quiz result — "
                "could you rephrase what you'd like?"
            }
        }

    graph = StateGraph(AgentState)
    graph.add_node("classify", classify_node)
    graph.add_node("recommend_next_topic", recommend_node)
    graph.add_node("generate_study_kit", study_kit_node)
    graph.add_node("submit_quiz", submit_quiz_node)
    graph.add_node("trigger_remediation", remediation_node)
    graph.add_node("other", other_node)

    graph.set_entry_point("classify")
    graph.add_conditional_edges(
        "classify",
        route_on_intent,
        {
            Intent.RECOMMEND_NEXT.value: "recommend_next_topic",
            Intent.GENERATE_STUDY_KIT.value: "generate_study_kit",
            Intent.SUBMIT_QUIZ.value: "submit_quiz",
            Intent.OTHER.value: "other",
        },
    )
    graph.add_edge("recommend_next_topic", END)
    graph.add_edge("generate_study_kit", END)
    graph.add_conditional_edges(
        "submit_quiz", route_after_quiz, {"remediate": "trigger_remediation", "end": END}
    )
    graph.add_edge("trigger_remediation", END)
    graph.add_edge("other", END)

    return graph.compile()


async def run_agent(
    db: AsyncSession,
    llm_client: LLMClient,
    vectorstore: VectorStoreClient,
    message: str,
    student_id: uuid.UUID,
    topic_id: uuid.UUID | None = None,
    kit_type: StudyKitType | None = None,
    quiz_submission: QuizSubmission | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Classify `message` and run it through the graph, returning the final result payload."""
    compiled = build_agent_graph(db, llm_client, vectorstore, settings)
    final_state: AgentState = await compiled.ainvoke(
        {
            "message": message,
            "student_id": student_id,
            "topic_id": topic_id,
            "kit_type": kit_type,
            "quiz_submission": quiz_submission,
        }
    )
    if final_state.get("error"):
        logger.error("Agent graph finished with an error", extra={"error": final_state["error"]})
    return final_state.get("result", {})
