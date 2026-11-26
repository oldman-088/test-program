import { useCallback, useEffect, useState } from 'react';
import { api, type HealthDbResponse, type HealthResponse } from '../lib/api';

export interface HealthState {
  health: HealthResponse | null;
  healthDb: HealthDbResponse | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

/**
 * Reads /api/health and /api/health/db (docs/API.md §1–2).
 * Shows real backend state — never fake data. On failure, `error` holds the
 * unified-template message and health fields stay null.
 */
export function useHealth(): HealthState {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthDb, setHealthDb] = useState<HealthDbResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [h, db] = await Promise.all([api.getHealth(), api.getHealthDb()]);
      setHealth(h);
      setHealthDb(db);
    } catch (err) {
      setHealth(null);
      setHealthDb(null);
      setError(err instanceof Error ? err.message : 'Backend is not reachable');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { health, healthDb, loading, error, refresh };
}
