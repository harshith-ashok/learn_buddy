/**
 * Mirrors of the backend's Pydantic schemas (see `wiki/api-reference.md`).
 * Kept as one file since they're pure data shapes with no logic of their
 * own — split only if a domain grows enough to warrant its own file.
 */

export type DocumentStatus = "pending" | "processing" | "done" | "failed";

export interface DocumentOut {
  id: string;
  filename: string;
  status: DocumentStatus;
  exam_date: string | null;
}

export interface SubtopicOut {
  id: string;
  name: string;
  description: string | null;
  position: number;
}

export interface TopicNodeOut {
  id: string;
  name: string;
  description: string | null;
  position: number;
  mastery_score: number;
  subtopics: SubtopicOut[];
  prerequisite_ids: string[];
}

export interface CourseGraphResponse {
  course_id: string;
  topics: TopicNodeOut[];
}

export interface TopicProgressOut {
  topic_id: string;
  topic_name: string;
  document_id: string;
  mastery_score: number;
  consecutive_failures: number;
}

export interface ProgressResponse {
  student_id: string;
  topics: TopicProgressOut[];
}

export interface Recommendation {
  topic_id: string;
  topic_name: string;
  mastery_score: number;
  justification: string;
}

export interface NoRecommendation {
  reason: string;
}

export type RecommendationResponse = Recommendation | NoRecommendation;

export function isRecommendation(
  value: RecommendationResponse,
): value is Recommendation {
  return "topic_id" in value;
}

export type StudyKitType = "summary" | "flashcards" | "quiz" | "problem_guide";

export interface Formula {
  label: string;
  latex: string;
  description: string;
}

export interface SummaryPoint {
  text: string;
  source_chunk_ids: string[];
}
export interface SummaryContent {
  points: SummaryPoint[];
  formulas: Formula[];
}

export interface Flashcard {
  question: string;
  answer: string;
  source_chunk_ids: string[];
}
export interface FlashcardsContent {
  cards: Flashcard[];
}

export interface QuizQuestion {
  question: string;
  options: string[];
  source_chunk_ids: string[];
  // correct_index is deliberately absent — the API never sends it, see
  // decisions/0007-server-side-quiz-grading.md.
}
export interface QuizContent {
  questions: QuizQuestion[];
}

export interface ProblemStep {
  text: string;
  source_chunk_ids: string[];
}
export interface Problem {
  prompt: string;
  steps: ProblemStep[];
}
export interface ProblemGuideContent {
  problems: Problem[];
  formulas: Formula[];
}

export type StudyKitContent =
  | SummaryContent
  | FlashcardsContent
  | QuizContent
  | ProblemGuideContent;

export interface StudyKitOut {
  id: string;
  topic_id: string;
  kit_type: StudyKitType;
  content: StudyKitContent;
  source_chunk_ids: string[];
}

export interface NotCovered {
  message: string;
}

export type GenerateStudyKitResponse = StudyKitOut | NotCovered;

export function isStudyKit(
  value: GenerateStudyKitResponse,
): value is StudyKitOut {
  return "id" in value;
}

export interface QuizAnswer {
  question_index: number;
  selected_index: number;
}

export interface RemediationPlan {
  topic_id: string;
  reason: string;
  message: string;
  suggested_actions: string[];
}

export interface QuizSubmitResponse {
  score: number;
  is_pass: boolean;
  previous_mastery_score: number;
  new_mastery_score: number;
  consecutive_failures: number;
  remediation: RemediationPlan | null;
}

export type ChatRole = "user" | "assistant";

export interface RelatedTopicOut {
  topic_id: string;
  topic_name: string;
}

export interface ChatMessageOut {
  id: string;
  topic_id: string;
  role: ChatRole;
  content: string;
  source_chunk_ids: string[];
  related_topics: RelatedTopicOut[];
  covered: boolean;
}

export type FeynmanVerdict = "correct" | "incomplete" | "incorrect";

export interface FeynmanBreakdownPoint {
  claim: string;
  verdict: FeynmanVerdict;
  feedback: string;
  source_chunk_ids: string[];
}

export interface FeynmanGradeResponse {
  covered: boolean;
  accuracy_score: number;
  overall_feedback: string;
  breakdown: FeynmanBreakdownPoint[];
  missing_concepts: string[];
  previous_mastery_score: number | null;
  new_mastery_score: number | null;
  consecutive_failures: number | null;
  remediation: RemediationPlan | null;
}

export interface FeynmanAttemptOut {
  id: string;
  topic_id: string;
  explanation: string;
  accuracy_score: number;
  overall_feedback: string;
  breakdown: FeynmanBreakdownPoint[];
  missing_concepts: string[];
}

export type WorkedStepVerdict = "correct" | "incorrect" | "unclear";

export interface WorkedStepFeedback {
  step_number: number;
  student_text: string;
  verdict: WorkedStepVerdict;
  feedback: string;
}

export interface WorkedAnswerGradeResponse {
  covered: boolean;
  is_correct: boolean;
  accuracy_score: number;
  overall_feedback: string;
  step_feedback: WorkedStepFeedback[];
  first_error_step: number | null;
  previous_mastery_score: number | null;
  new_mastery_score: number | null;
  consecutive_failures: number | null;
  remediation: RemediationPlan | null;
}

export interface WorkedAnswerAttemptOut {
  id: string;
  study_kit_id: string;
  problem_index: number;
  work: string;
  is_correct: boolean;
  accuracy_score: number;
  overall_feedback: string;
  step_feedback: WorkedStepFeedback[];
  first_error_step: number | null;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface ApiErrorBody {
  code: string;
  message: string;
  details?: unknown;
}
