import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  setTokens,
} from "@/lib/token-store";
import type {
  ApiErrorBody,
  ChatMessageOut,
  CourseGraphResponse,
  DocumentOut,
  FeynmanAttemptOut,
  FeynmanGradeResponse,
  GenerateStudyKitResponse,
  ProgressResponse,
  QuizAnswer,
  QuizSubmitResponse,
  RecommendationResponse,
  StudyKitOut,
  StudyKitType,
  TokenResponse,
  WorkedAnswerAttemptOut,
  WorkedAnswerGradeResponse,
} from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly details?: unknown;

  constructor(body: ApiErrorBody, status: number) {
    super(body.message);
    this.name = "ApiError";
    this.code = body.code;
    this.status = status;
    this.details = body.details;
  }
}

let refreshInFlight: Promise<boolean> | null = null;

/** Exchange the stored refresh token for a new pair, de-duplicating concurrent callers. */
async function refreshSession(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;

  refreshInFlight ??= (async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!response.ok) {
        clearTokens();
        return false;
      }
      setTokens((await response.json()) as TokenResponse);
      return true;
    } catch {
      return false;
    } finally {
      refreshInFlight = null;
    }
  })();

  return refreshInFlight;
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  query?: Record<string, string | undefined>;
  auth?: boolean;
  /** Internal: marks a request as already retried once after a refresh. */
  _retried?: boolean;
}

function buildUrl(path: string, query?: Record<string, string | undefined>): string {
  const url = new URL(path, API_BASE_URL);
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined) url.searchParams.set(key, value);
  }
  return url.toString();
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, query, auth = true, _retried = false } = options;

  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (auth) {
    const token = getAccessToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(buildUrl(path, query), {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (response.status === 401 && auth && !_retried && getRefreshToken()) {
    const refreshed = await refreshSession();
    if (refreshed) return request<T>(path, { ...options, _retried: true });
  }

  if (!response.ok) {
    const errorBody = (await response.json().catch(() => null)) as ApiErrorBody | null;
    throw new ApiError(
      errorBody ?? { code: "unknown_error", message: response.statusText },
      response.status,
    );
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

async function requestForm<T>(path: string, formData: FormData): Promise<T> {
  const headers: Record<string, string> = {};
  const token = getAccessToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(buildUrl(path), { method: "POST", headers, body: formData });
  if (!response.ok) {
    const errorBody = (await response.json().catch(() => null)) as ApiErrorBody | null;
    throw new ApiError(
      errorBody ?? { code: "unknown_error", message: response.statusText },
      response.status,
    );
  }
  return (await response.json()) as T;
}

export const authApi = {
  register: (email: string, password: string, fullName: string) =>
    request<TokenResponse>("/auth/register", {
      method: "POST",
      auth: false,
      body: { email, password, full_name: fullName },
    }),
  login: (email: string, password: string) =>
    request<TokenResponse>("/auth/login", {
      method: "POST",
      auth: false,
      body: { email, password },
    }),
  logout: (refreshToken: string) =>
    request<void>("/auth/logout", { method: "POST", auth: false, body: { refresh_token: refreshToken } }),
};

export const documentsApi = {
  list: () => request<DocumentOut[]>("/documents"),
  get: (documentId: string) => request<DocumentOut>(`/documents/${documentId}`),
  upload: (file: File, examDate?: string) => {
    const formData = new FormData();
    formData.append("file", file);
    if (examDate) formData.append("exam_date", examDate);
    return requestForm<{ id: string; filename: string; status: string; created: boolean }>(
      "/documents/upload",
      formData,
    );
  },
};

export const graphApi = {
  getCourseGraph: (courseId: string) => request<CourseGraphResponse>(`/graph/${courseId}`),
};

export const progressApi = {
  get: (studentId: string) => request<ProgressResponse>(`/progress/${studentId}`),
};

export const recommendationApi = {
  getNext: () => request<RecommendationResponse>("/recommendation/next"),
};

export const studyKitApi = {
  generate: (topicId: string, kitType: StudyKitType) =>
    request<GenerateStudyKitResponse>("/study-kit/generate", {
      method: "POST",
      body: { topic_id: topicId, kit_type: kitType },
    }),
  listForTopic: (topicId: string) =>
    request<StudyKitOut[]>("/study-kit", { query: { topic_id: topicId } }),
  get: (studyKitId: string) => request<StudyKitOut>(`/study-kit/${studyKitId}`),
};

export const quizApi = {
  submit: (topicId: string, studyKitId: string, answers: QuizAnswer[]) =>
    request<QuizSubmitResponse>("/quiz/submit", {
      method: "POST",
      body: { topic_id: topicId, study_kit_id: studyKitId, answers },
    }),
};

export const chatApi = {
  ask: (topicId: string, message: string) =>
    request<ChatMessageOut>("/chat/ask", {
      method: "POST",
      body: { topic_id: topicId, message },
    }),
  listForTopic: (topicId: string) =>
    request<ChatMessageOut[]>("/chat", { query: { topic_id: topicId } }),
};

export const feynmanApi = {
  grade: (topicId: string, explanation: string) =>
    request<FeynmanGradeResponse>("/feynman/grade", {
      method: "POST",
      body: { topic_id: topicId, explanation },
    }),
  listForTopic: (topicId: string) =>
    request<FeynmanAttemptOut[]>("/feynman", { query: { topic_id: topicId } }),
};

export const workedAnswerApi = {
  grade: (studyKitId: string, problemIndex: number, work: string) =>
    request<WorkedAnswerGradeResponse>("/worked-answer/grade", {
      method: "POST",
      body: { study_kit_id: studyKitId, problem_index: problemIndex, work },
    }),
  listForProblem: (studyKitId: string, problemIndex: number) =>
    request<WorkedAnswerAttemptOut[]>("/worked-answer", {
      query: { study_kit_id: studyKitId, problem_index: String(problemIndex) },
    }),
};
