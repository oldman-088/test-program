/**
 * Single API client for NEXUS OSINT.
 *
 * Follows the fixed contract in docs/API.md (main) literally:
 *   - every path lives under the /api/v1 prefix;
 *   - public endpoints (no auth): GET /api/v1/health, GET /api/v1/health/ready;
 *   - every other endpoint requires the X-API-Key header (from VITE_API_KEY);
 *   - every error response uses the unified envelope:
 *       { "error": { "code", "message", "details": [], "request_id" } }
 *     where `details` is an array (possibly empty) and `request_id` may be null.
 *
 * Base URL comes from VITE_API_BASE_URL (see frontend/.env.example).
 * When empty, relative /api/v1/... URLs are used (Vite dev proxy in dev).
 * No localhost/127.0.0.1 is hardcoded in this file.
 */

export type QueryType =
  | 'name'
  | 'username'
  | 'email'
  | 'phone'
  | 'url'
  | 'domain'
  | 'entity';

export type InvestigationStatus = 'queued' | 'running' | 'completed' | 'failed';
export type HealthStatus = 'ok' | 'degraded' | 'error';
export type IntegrationStatus = 'available' | 'unavailable' | 'disabled';
export type AiProviderStatus = 'available' | 'unavailable' | 'not_configured';
export type TaskStatus = 'queued' | 'running' | 'completed' | 'failed';
export type ReportStatus = 'ready' | 'generating' | 'failed';

/** GET /api/v1/health — public, no auth. */
export interface HealthResponse {
  status: HealthStatus;
  version: string;
  environment: string;
}

/** GET /api/v1/health/ready — public, no auth. */
export interface HealthReadyResponse {
  status: 'ready';
  database: 'up';
}

export interface RecentInvestigation {
  id: string;
  query: string;
  query_type: QueryType;
  status: InvestigationStatus;
  created_at: string;
}

export interface RecentInvestigationsResponse {
  items: RecentInvestigation[];
  total: number;
}

export interface StatsResponse {
  total_investigations: number;
  total_searches: number;
  success_rate: number;
  avg_duration_ms: number;
}

export interface Integration {
  id: string;
  name: string;
  status: IntegrationStatus;
  description: string;
}

export interface IntegrationsResponse {
  items: Integration[];
}

export interface AiProviderResponse {
  provider: string;
  model: string;
  status: AiProviderStatus;
  latency_ms: number | null;
}

export interface TaskProgressItem {
  id: string;
  name: string;
  status: TaskStatus;
  progress: number;
}

export interface TaskProgressResponse {
  items: TaskProgressItem[];
  total: number;
}

export interface LatestReport {
  id: string;
  title: string;
  status: ReportStatus;
  created_at: string;
}

export interface LatestReportsResponse {
  items: LatestReport[];
  total: number;
}

export interface CreateInvestigationRequest {
  query: string;
  query_type: QueryType;
}

export interface CreateInvestigationResponse {
  id: string;
  query: string;
  query_type: QueryType;
  status: InvestigationStatus;
  created_at: string;
}

/** One entry of the unified error envelope's `details` array. */
export interface ErrorDetail {
  field?: string;
  loc?: string[];
  message?: string;
  type?: string;
}

/** Error matching the unified template in docs/API.md (main). */
export class ApiError extends Error {
  status: number;
  code: string;
  details: ErrorDetail[];
  requestId: string | null;

  constructor(
    status: number,
    code: string,
    message: string,
    details: ErrorDetail[] = [],
    requestId: string | null = null,
  ) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
    this.requestId = requestId;
  }
}

function baseUrl(): string {
  const raw = import.meta.env.VITE_API_BASE_URL ?? '';
  return raw.replace(/\/$/, '');
}

function apiKey(): string {
  const raw = import.meta.env.VITE_API_KEY ?? '';
  return raw.replace(/\/$/, '');
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object';
}

/**
 * Endpoints that the contract declares public (Auth: no) — they are called
 * without the X-API-Key header. Matched by exact path, never by prefix.
 */
const PUBLIC_PATHS: ReadonlySet<string> = new Set([
  '/api/v1/health',
  '/api/v1/health/ready',
]);

/** Parse a response body against the unified error template (docs/API.md §2). */
export function parseApiError(status: number, body: unknown): ApiError {
  if (isRecord(body) && isRecord(body.error)) {
    const err = body.error;
    const code = typeof err.code === 'string' ? err.code : 'UNKNOWN_ERROR';
    const message = typeof err.message === 'string' ? err.message : 'Request failed';
    const details: ErrorDetail[] = Array.isArray(err.details)
      ? err.details.filter(isRecord).map((d) => d as ErrorDetail)
      : [];
    const requestId = typeof err.request_id === 'string' ? err.request_id : null;
    return new ApiError(status, code, message, details, requestId);
  }
  return new ApiError(status, 'UNKNOWN_ERROR', `Request failed with status ${status}`);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((init?.headers as Record<string, string> | undefined) ?? {}),
  };
  // Contract: every /api/v1 path except the two public health endpoints
  // requires the X-API-Key header.
  if (!PUBLIC_PATHS.has(path)) {
    const key = apiKey();
    if (key) {
      headers['X-API-Key'] = key;
    }
  }

  let response: Response;
  try {
    response = await fetch(`${baseUrl()}${path}`, {
      headers,
      ...init,
    });
  } catch {
    throw new ApiError(0, 'NETWORK_ERROR', 'Backend is not reachable');
  }

  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }

  if (!response.ok) {
    throw parseApiError(response.status, body);
  }
  return body as T;
}

export const api = {
  getHealth: () => request<HealthResponse>('/api/v1/health'),
  getHealthReady: () => request<HealthReadyResponse>('/api/v1/health/ready'),
  getRecentInvestigations: (limit = 5) =>
    request<RecentInvestigationsResponse>(`/api/v1/investigations/recent?limit=${limit}`),
  getStats: () => request<StatsResponse>('/api/v1/stats'),
  getIntegrations: () => request<IntegrationsResponse>('/api/v1/integrations'),
  getAiProvider: () => request<AiProviderResponse>('/api/v1/ai/provider'),
  getTaskProgress: () => request<TaskProgressResponse>('/api/v1/tasks/progress'),
  getLatestReports: (limit = 5) =>
    request<LatestReportsResponse>(`/api/v1/reports/latest?limit=${limit}`),
  createInvestigation: (payload: CreateInvestigationRequest) =>
    request<CreateInvestigationResponse>('/api/v1/investigations', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
};
