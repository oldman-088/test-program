import type { Difficulty } from "../game/types";

export interface LeaderboardEntry {
  id: number;
  player_name: string;
  difficulty: Difficulty;
  attempts: number;
  duration_seconds: number;
  finished_at: string;
  rank: number;
}

export interface Leaderboard {
  difficulty: Difficulty;
  limit: number;
  total: number;
  entries: LeaderboardEntry[];
}

export interface ScorePayload {
  player_name: string;
  difficulty: Difficulty;
  attempts: number;
  duration_seconds: number;
  finished_at?: string;
}

/** Relative by default so the Vite proxy / same-origin API serves it. */
const API_BASE: string = (import.meta.env["VITE_API_BASE_URL"] as string | undefined) ?? "";

export class ScoreApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = "ScoreApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });

  if (!response.ok) {
    throw new ScoreApiError(`Request failed with status ${response.status}`, response.status);
  }
  return (await response.json()) as T;
}

export function submitScore(payload: ScorePayload): Promise<LeaderboardEntry> {
  return request<LeaderboardEntry>("/api/v1/scores", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchLeaderboard(
  difficulty: Difficulty,
  limit = 10,
  signal?: AbortSignal,
): Promise<Leaderboard> {
  const query = new URLSearchParams({ difficulty, limit: String(limit) });
  const init: RequestInit = signal ? { signal } : {};
  return request<Leaderboard>(`/api/v1/leaderboard?${query.toString()}`, init);
}

export function isScoreApiError(error: unknown): error is ScoreApiError {
  return error instanceof ScoreApiError;
}
