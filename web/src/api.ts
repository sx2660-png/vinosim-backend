export const PUBLIC_API_BASE = "https://identity-surrounding-backup-later.trycloudflare.com";

export function apiBase(): string {
  const fromEnv = import.meta.env.VITE_API_BASE;
  if (fromEnv) return fromEnv.replace(/\/$/, "");
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
};

export type QuizQuestion = {
  id: number;
  question: string;
  options: string[];
  category: string;
};

export type QuizResult = {
  correct: boolean;
  correct_answer: string;
  explanation: string;
  score: { correct: number; total: number };
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
  wine_recommendations?: string[];
  sources?: string[];
  confidence?: string;
  retrieved_titles?: string[];
  character?: string;
  emotion?: string;
};

export type HistoryMessage = { role: string; content: string };

export function getArticles(category?: string) {
  const query = category ? `?category=${encodeURIComponent(category)}` : "";
  return read<{ articles: Article[] }>(`/articles${query}`);
}

export function getQuiz() {
  return read<QuizQuestion>("/quiz");
}

export function submitQuiz(questionId: number, answer: string) {
  return read<QuizResult>("/quiz/submit", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ user_id: userId(), question_id: questionId, answer }),
  });
}

export function askSommelier(mode: "correction" | "roleplay", message: string) {
  return read<AgentReply>("/agent", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ user_id: userId(), mode, message }),
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
