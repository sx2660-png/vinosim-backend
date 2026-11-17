export const PUBLIC_API_BASE = "https://vinosim-backend-production.up.railway.app";

export function apiBase(): string {
  const fromEnv = import.meta.env.VITE_API_BASE;
  if (fromEnv) return fromEnv.replace(/\/$/, "");
  // `npm run dev` proxies the API routes to 127.0.0.1:8000, so the page and the API share one origin.
  if (import.meta.env.DEV) return "";
  // A production build opened on this machine talks to the local API directly.
  if (location.hostname === "localhost" || location.hostname === "127.0.0.1") {
    return "http://127.0.0.1:8000";
  }
  return PUBLIC_API_BASE;
}

export function userId(): string {
  const key = "vinosim_user_id";
  let id = localStorage.getItem(key);
  if (!id) {
    id = `user_${Math.random().toString(36).slice(2, 10)}`;
    localStorage.setItem(key, id);
  }
  return id;
}

async function read<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase()}${path}`, init);
  const text = await response.text();
  if (!response.ok) {
    let message = text || response.statusText;
    try {
      const body = JSON.parse(text) as { detail?: unknown };
      if (typeof body.detail === "string") message = body.detail;
    } catch {
      /* keep the raw response text */
    }
    throw new Error(message);
  }
  return (text ? JSON.parse(text) : null) as T;
}

export type Article = {
  id: number;
  title: string;
  category: string;
  content: string;
  image: string;
  match?: string[];
};

export type QuizQuestion = {
  id: number;
  question: string;
  options: string[];
  category?: string;
  image?: string;
  app_level?: number;
  item_type?: string;
  sheet_line?: string;
};

export type QuizResult = {
  correct: boolean;
  correct_answer: string;
  explanation: string;
  score: { correct: number; total: number };
  new_medals?: string[];
};

export type WineLabel = {
  producer: string;
  wine_name: string;
  vintage: string;
  region: string;
  grape_varieties: string[];
  alcohol: string;
  notes: string;
};

export type LabelQuiz = {
  question: string;
  options: string[];
  correct_answer: string;
  explanation: string;
};

export type AgentReply = {
  answer?: string;
  reply?: string;
  sources?: string[];
  confidence?: string;
  retrieved_titles?: string[];
  character?: string;
  emotion?: string;
};

export type HistoryMessage = { role: string; content: string };

export function getArticles(category?: string) {
  const params = new URLSearchParams({ user_id: userId() });
  if (category) params.set("category", category);
  return read<{ articles: Article[] }>(`/articles?${params}`);
}

export function getQuiz(level?: number) {
  return read<QuizQuestion>(level ? `/quiz?level=${level}` : "/quiz");
}

export function submitQuiz(questionId: number, answer: string) {
  return read<QuizResult>("/quiz/submit", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ user_id: userId(), question_id: questionId, answer }),
  });
}

export function askSommelier(mode: "correction" | "roleplay", message: string, step?: SheetLine) {
  return read<AgentReply>("/agent", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ user_id: userId(), mode, message, step: step ?? null }),
  });
}

export function chatHistory(mode: "correction" | "roleplay") {
  const query = new URLSearchParams({ user_id: userId(), mode });
  return read<{ messages: HistoryMessage[] }>(`/agent/history?${query}`);
}

export function scanLabel(file: File) {
  const body = new FormData();
  body.append("file", file);
  return read<WineLabel>("/scan", { method: "POST", body });
}

export function decodeLabel(file: File) {
  const body = new FormData();
  body.append("file", file);
  return read<LabelQuiz>("/label/decode", { method: "POST", body });
}

export function checkHealth() {
  return read<{ ok: boolean }>("/health");
}

// --- Levels, exams, tasting sheets, medals ---

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify(body),
});

export type SheetLine = "appearance" | "nose" | "palate" | "liking";

export type ExamSummary = { score: number; total: number; passed: boolean; at: string } | null;

export type Progress = {
  level1: { exam: ExamSummary; sheets_complete: number; sheets_needed: number; medal: string | null };
  level2: {
    unlocked: boolean;
    exam: ExamSummary;
    labels_done: number;
    labels_needed: number;
    medal: string | null;
  };
  bonus: { status: string; articles: { id: number; title: string; read: boolean; medal: string | null }[] };
  course_complete: boolean;
  new_medals: string[];
};

export type ExamPaper = {
  attempt_id: number;
  level: number;
  pass_pct: number;
  time_limit_min: number | null;
  questions: QuizQuestion[];
};

export type ExamResult = {
  level: number;
  score: number;
  total: number;
  pass_pct: number;
  passed: boolean;
  review: { id: number; given: string; correct_answer: string; correct: boolean; explanation: string }[];
  new_medals: string[];
};

export type Sheet = {
  id: number;
  wine_name: string;
  appearance: string;
  nose: string;
  palate: string;
  palate_because: string;
  liking: string;
  structure_words: string[];
  complete: boolean;
  created_at: string;
  updated_at: string;
};

export type SheetDraft = Omit<Sheet, "id" | "structure_words" | "complete" | "created_at" | "updated_at"> & {
  id?: number;
};

export type BonusArticle = { id: number; title: string; content: string; image: string; read: boolean };

export type TastingPrompt = { id: number; sheet_line: string; prompt: string; examples: string[]; guidance: string };

export function getProgress() {
  return read<Progress>(`/progress?user_id=${encodeURIComponent(userId())}`);
}

export function startExam(level: number) {
  return read<ExamPaper>("/exam/start", json({ user_id: userId(), level }));
}

export function submitExam(attemptId: number, answers: Record<string, string>) {
  return read<ExamResult>("/exam/submit", json({ user_id: userId(), attempt_id: attemptId, answers }));
}

export function getSheets() {
  return read<{ sheets: Sheet[] }>(`/sheets?user_id=${encodeURIComponent(userId())}`);
}

export function saveSheet(draft: SheetDraft) {
  return read<{ sheet: Sheet; missing: string[]; new_medals: string[] }>(
    "/sheets",
    json({ user_id: userId(), ...draft }),
  );
}

export function getLabelTasks() {
  return read<{ needed: number; done: number; tasks: (QuizQuestion & { done: boolean })[] }>(
    `/labels/tasks?user_id=${encodeURIComponent(userId())}`,
  );
}

export function getBonus() {
  return read<{ status: string; articles: BonusArticle[] }>(`/bonus?user_id=${encodeURIComponent(userId())}`);
}

export function markBonusRead(articleId: number) {
  return read<{ ok: boolean; new_medals: string[] }>("/bonus/read", json({ user_id: userId(), article_id: articleId }));
}

export function getPrompts(line?: SheetLine) {
  return read<{ prompts: TastingPrompt[] }>(line ? `/prompts?line=${line}` : "/prompts");
}
