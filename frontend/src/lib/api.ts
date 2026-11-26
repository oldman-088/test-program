/**
 * Single API client for NEXUS OSINT.
 *
 * Follows docs/API.md literally: same paths, same field names, same unified
 * error template:
 *   { "error": { "code": string, "message": string, "details": string | null } }
 *
 * Base URL comes from VITE_API_BASE_URL (see frontend/.env.example).
 * When empty, relative /api/... URLs are used (Vite dev proxy in dev).
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

export interface HealthResponse {
  status: HealthStatus;
  version: string;
  timestamp: string;
}

export interface HealthDbResponse {
  status: HealthStatus;
  database: string;
  latency_ms: number;
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

/** Error matching the unified template in docs/API.md. */
export class ApiError extends Error {
  status: number;
  code: string;
  details: string | null;

  constructor(status: number, code: string, message: string, details: string | null = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

function baseUrl(): string {
  const raw = import.meta.env.VITE_API_BASE_URL ?? '';
  return raw.replace(/\/$/, '');
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object';
}

/** Parse a response body against the unified error template. */
export function parseApiError(status: number, body: unknown): ApiError {
  if (isRecord(body) && isRecord(body.error)) {
    const err = body.error;
    const code = typeof err.code === 'string' ? err.code : 'UNKNOWN_ERROR';
    const message = typeof err.message === 'string' ? err.message : 'Request failed';
    const details = typeof err.details === 'string' ? err.details : null;
    return new ApiError(status, code, message, details);
  }
  return new ApiError(status, 'UNKNOWN_ERROR', `Request failed with status ${status}`);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${baseUrl()}${path}`, {
      headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
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
  getHealth: () => request<HealthResponse>('/api/health'),
  getHealthDb: () => request<HealthDbResponse>('/api/health/db'),
  getRecentInvestigations: (limit = 5) =>
    request<RecentInvestigationsResponse>(`/api/investigations/recent?limit=${limit}`),
  getStats: () => request<StatsResponse>('/api/stats'),
  getIntegrations: () => request<IntegrationsResponse>('/api/integrations'),
  getAiProvider: () => request<AiProviderResponse>('/api/ai/provider'),
  getTaskProgress: () => request<TaskProgressResponse>('/api/tasks/progress'),
  getLatestReports: (limit = 5) =>
    request<LatestReportsResponse>(`/api/reports/latest?limit=${limit}`),
  createInvestigation: (payload: CreateInvestigationRequest) =>
    request<CreateInvestigationResponse>('/api/investigations', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
};
