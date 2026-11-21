import { ScorePayload } from '../game/types';

export interface ScoreSubmitResult {
  ok: boolean;
  error?: string;
}

const DEFAULT_SCORE_ENDPOINT = import.meta.env.VITE_SCORE_API_URL || '/api/scores';

export async function submitScore(
  payload: ScorePayload,
  endpoint: string = DEFAULT_SCORE_ENDPOINT
): Promise<ScoreSubmitResult> {
  try {
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      return {
        ok: false,
        error: `HTTP ${response.status}`,
      };
    }

    return { ok: true };
  } catch (err) {
    return {
      ok: false,
      error: err instanceof Error ? err.message : 'Network error',
    };
  }
}
