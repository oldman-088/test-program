import { useCallback, useEffect, useState } from 'react';
import { api, type HealthReadyResponse, type HealthResponse } from '../lib/api';

export interface HealthState {
  health: HealthResponse | null;
  healthReady: HealthReadyResponse | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

/**
 * Reads GET /api/v1/health and GET /api/v1/health/ready — the two public
 * endpoints of the contract (docs/API.md, main). Shows real backend state —
 * never fake data. On failure, `error` holds the unified-template message and
 * health fields stay null.
 */
export function useHealth(): HealthState {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthReady, setHealthReady] = useState<HealthReadyResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [h, ready] = await Promise.all([api.getHealth(), api.getHealthReady()]);
      setHealth(h);
      setHealthReady(ready);
    } catch (err) {
      setHealth(null);
      setHealthReady(null);
      setError(err instanceof Error ? err.message : 'Backend is not reachable');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { health, healthReady, loading, error, refresh };
}
