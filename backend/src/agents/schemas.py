import uuid
from enum import Enum as PyEnum

from pydantic import BaseModel, Field


class Intent(str, PyEnum):
    """The fixed enum the classifier routes on — never an open-ended label."""

    RECOMMEND_NEXT = "recommend_next"
    GENERATE_STUDY_KIT = "generate_study_kit"
    SUBMIT_QUIZ = "submit_quiz"
    OTHER = "other"


class IntentClassification(BaseModel):
    """The classifier's structured output, validated before anything routes on it."""

    intent: Intent
    confidence: float = Field(ge=0.0, le=1.0)


class RetrievedChunk(BaseModel):
    """One grounding chunk returned by retrieval, with its source citation."""

    chunk_id: str
    document_id: uuid.UUID
    text: str
    section_heading: str | None
    similarity: float


class RetrievalResult(BaseModel):
    """What retrieval found for a query, and whether it clears the coverage guardrail."""

    chunks: list[RetrievedChunk] = Field(default_factory=list)
    covered: bool

    @property
    def source_chunk_ids(self) -> list[str]:
        return [chunk.chunk_id for chunk in self.chunks]


class Recommendation(BaseModel):
    """`recommend_next_topic`'s output: the next topic plus why."""

    topic_id: uuid.UUID
    topic_name: str
    mastery_score: float
    justification: str


class NoRecommendation(BaseModel):
    """No topic is currently ready to recommend (nothing ingested, or everything mastered)."""

    reason: str


class Formula(BaseModel):
    """One formula worth calling out separately from prose — rendered as LaTeX on the frontend.

    `latex` is the bare expression (e.g. `E = mc^2`), no `$`/`\\[` delimiters
    — the frontend's renderer owns display-vs-inline mode, not the model.
    """

    label: str
    latex: str
    description: str = ""


class SummaryPoint(BaseModel):
    text: str
    source_chunk_ids: list[str] = Field(default_factory=list)


class SummaryContent(BaseModel):
    points: list[SummaryPoint]
    # Populated only when the topic's material actually contains formulas
    # worth isolating (math/science topics) — empty otherwise, never
    # invented to fill the field. See `agents.study_kit._FORMULA_INSTRUCTION`.
    formulas: list[Formula] = Field(default_factory=list)


class Flashcard(BaseModel):
    question: str
    answer: str
    source_chunk_ids: list[str] = Field(default_factory=list)


class FlashcardsContent(BaseModel):
    cards: list[Flashcard]


class QuizQuestion(BaseModel):
    question: str
    options: list[str] = Field(min_length=2)
    correct_index: int
    source_chunk_ids: list[str] = Field(default_factory=list)


class QuizContent(BaseModel):
    questions: list[QuizQuestion]


class ProblemStep(BaseModel):
    text: str
    source_chunk_ids: list[str] = Field(default_factory=list)


class Problem(BaseModel):
    prompt: str
    steps: list[ProblemStep]


class ProblemGuideContent(BaseModel):
    problems: list[Problem]
    formulas: list[Formula] = Field(default_factory=list)


class StudyKitResult(BaseModel):
    """A generated study kit, ready to persist as a `StudyKit` row."""

    kit_type: str
    content: SummaryContent | FlashcardsContent | QuizContent | ProblemGuideContent
    source_chunk_ids: list[str]


class NotCovered(BaseModel):
    """The guardrail's explicit response when nothing clears the similarity threshold.

    Returned instead of calling the model — a generated guess grounded in
    nothing is worse than an honest "not covered".
    """

    message: str = "This isn't covered in your uploaded materials yet."


class QuizAnswer(BaseModel):
    question_index: int
    selected_index: int


class QuizSubmission(BaseModel):
    study_kit_id: uuid.UUID | None
    answers: list[QuizAnswer]
    score: float = Field(ge=0.0, le=1.0)


class MasteryUpdateResult(BaseModel):
    """What `score_and_update_mastery` changed, and whether remediation should fire."""

    topic_id: uuid.UUID
    previous_score: float
    new_score: float
    is_pass: bool
    consecutive_failures: int
    mastery_drop: float
    remediation_triggered: bool


class RemediationPlan(BaseModel):
    """`trigger_remediation`'s output: why it fired, and a revised mini-plan."""

    topic_id: uuid.UUID
    reason: str
    message: str
    suggested_actions: list[str]


class ChatAnswerContent(BaseModel):
    """The model's structured output for a topic-chat question.

    `answerable` is the model's own guardrail check, on top of the
    retrieval-coverage guardrail that runs before this is ever called: even
    when relevant excerpts exist, the question itself might not be a
    genuine question about them (e.g. an instruction-override attempt, or
    small talk). `answer`/`source_chunk_ids` are only trusted by the caller
    when `answerable` is true — see `agents.chat.answer_topic_question`.
    """

    answerable: bool
    answer: str = ""
    source_chunk_ids: list[str] = Field(default_factory=list)


class RelatedTopic(BaseModel):
    """A sibling topic (same document) whose material the chat answer also touched."""

    topic_id: uuid.UUID
    topic_name: str


class ChatAnswerResult(BaseModel):
    """`answer_topic_question`'s output, ready to persist as a `ChatMessage` row."""

    answer: str
    covered: bool
    source_chunk_ids: list[str] = Field(default_factory=list)
    related_topics: list[RelatedTopic] = Field(default_factory=list)


class FeynmanVerdict(str, PyEnum):
    CORRECT = "correct"
    INCOMPLETE = "incomplete"
    INCORRECT = "incorrect"


class FeynmanBreakdownPoint(BaseModel):
    """One claim pulled out of the student's explanation and checked against the excerpts."""

    claim: str
    verdict: FeynmanVerdict
    feedback: str
    source_chunk_ids: list[str] = Field(default_factory=list)


class FeynmanGradeContent(BaseModel):
    """The model's structured output for grading a Feynman-mode explanation.

    `gradable` is the model's own guardrail, same role as `ChatAnswerContent.answerable`:
    even with relevant excerpts to grade against, the submission might not
    actually be an explanation attempt (empty, gibberish, an
    instruction-override attempt) — everything else here is discarded by
    the caller when `gradable` is false. `accuracy_score` is this
    explanation's observed mastery signal, fed into
    `agents.mastery.apply_mastery_observation` exactly like a quiz score.
    """

    gradable: bool
    accuracy_score: float = Field(ge=0.0, le=1.0, default=0.0)
    overall_feedback: str = ""
    breakdown: list[FeynmanBreakdownPoint] = Field(default_factory=list)
    missing_concepts: list[str] = Field(default_factory=list)


class FeynmanGradeResult(BaseModel):
    """`grade_explanation`'s output, ready to persist as a `FeynmanAttempt` row."""

    covered: bool
    accuracy_score: float = 0.0
    overall_feedback: str = ""
    breakdown: list[FeynmanBreakdownPoint] = Field(default_factory=list)
    missing_concepts: list[str] = Field(default_factory=list)
    mastery: MasteryUpdateResult | None = None
    remediation: RemediationPlan | None = None


class WorkedStepVerdict(str, PyEnum):
    CORRECT = "correct"
    INCORRECT = "incorrect"
    UNCLEAR = "unclear"


class WorkedStepFeedback(BaseModel):
    """One step the model identified in the student's own written work."""

    step_number: int
    student_text: str
    verdict: WorkedStepVerdict
    feedback: str


class WorkedAnswerGradeContent(BaseModel):
    """The model's structured output for grading a student's worked solution.

    Graded against the reference `Problem` (prompt + steps) already stored
    on the `problem_guide` study kit — no fresh retrieval call, since that
    problem was itself generated from the topic's material already (see
    `agents.worked_answer.grade_worked_answer`). `gradable` is the same
    self-guardrail pattern as chat/Feynman.
    """

    gradable: bool
    is_correct: bool = False
    accuracy_score: float = Field(ge=0.0, le=1.0, default=0.0)
    overall_feedback: str = ""
    step_feedback: list[WorkedStepFeedback] = Field(default_factory=list)
    first_error_step: int | None = None


class WorkedAnswerGradeResult(BaseModel):
    """`grade_worked_answer`'s output, ready to persist as a `WorkedAnswerAttempt` row."""

    covered: bool
    is_correct: bool = False
    accuracy_score: float = 0.0
    overall_feedback: str = ""
    step_feedback: list[WorkedStepFeedback] = Field(default_factory=list)
    first_error_step: int | None = None
    mastery: MasteryUpdateResult | None = None
    remediation: RemediationPlan | None = None
