import { describe, expect, it, vi } from 'vitest';
import { ApiError, api, parseApiError } from './api';

/**
 * `src/lib/api.ts` contract tests — docs/API.md is the source of truth.
 *
 * Covered here:
 *  1. request construction (method, JSON headers, body, query string)
 *  2. base URL handling (`VITE_API_BASE_URL`, trailing slash, empty → relative)
 *  3. the unified error template documented in docs/API.md §"قالب الخطأ الموحد"
 *  4. never touching a real service: `fetch` is always replaced by a mock.
 */

type FetchMock = ReturnType<typeof vi.fn> & ((...args: never[]) => Promise<Response>);

function stubFetch(impl: (url: string, init?: RequestInit) => Response | Promise<Response>) {
  const fetchMock = vi.fn(impl as unknown as (...args: never[]) => Promise<Response>);
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock as unknown as FetchMock;
}

function jsonResponse(body: unknown, status = 200, headers: Record<string, string> = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json', ...headers },
  });
}

/** The exact error document from docs/API.md. */
const DOCUMENTED_ERROR = {
  error: {
    code: 'NOT_FOUND',
    message: 'Resource not found.',
    details: null,
  },
};

describe('api request construction', () => {
  it('GET /api/health sends a relative GET request with JSON content type', async () => {
    const fetchMock = stubFetch(() =>
      jsonResponse({ status: 'ok', version: '0.1.0', timestamp: '2026-11-26T00:00:00Z' }),
    );

    await expect(api.getHealth()).resolves.toMatchObject({ status: 'ok', version: '0.1.0' });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe('/api/health');
    expect(url.startsWith('/')).toBe(true); // relative: no hardcoded host
    expect(init).toMatchObject({ headers: { 'Content-Type': 'application/json' } });
    expect(init.method).toBeUndefined(); // GET is the fetch default
  });

  it('POST /api/investigations sends a JSON body and keeps the documented field names', async () => {
    const payload = { query: 'alice', query_type: 'username' as const };
    const fetchMock = stubFetch(() =>
      jsonResponse(
        { id: 'inv-1', ...payload, status: 'queued', created_at: '2026-11-26T00:00:00Z' },
        201,
      ),
    );

    await api.createInvestigation(payload);

    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe('/api/investigations');
    expect(init.method).toBe('POST');
    expect(init.headers).toMatchObject({ 'Content-Type': 'application/json' });
    expect(typeof init.body).toBe('string');
    expect(JSON.parse(init.body as string)).toEqual({ query: 'alice', query_type: 'username' });
  });

  it('encodes the documented `limit` query parameter', async () => {
    const fetchMock = stubFetch(() => jsonResponse({ items: [], total: 0 }));

    await api.getRecentInvestigations(5);
    await api.getLatestReports(3);

    const urls = fetchMock.mock.calls.map((call) => (call as unknown as [string])[0]);
    expect(urls[0]).toBe('/api/investigations/recent?limit=5');
    expect(urls[1]).toBe('/api/reports/latest?limit=3');
  });

  it('returns the parsed JSON body on success without an envelope', async () => {
    stubFetch(() => jsonResponse({ total_investigations: 7, total_searches: 9 }));

    const stats = await api.getStats();
    expect(stats.total_investigations).toBe(7);
    expect(stats.total_searches).toBe(9);
  });

  it('sends every documented GET path exactly as docs/API.md lists it', async () => {
    const fetchMock = stubFetch(() => jsonResponse({}));

    await api.getHealthDb();
    await api.getStats();
    await api.getIntegrations();
    await api.getAiProvider();
    await api.getTaskProgress();

    const urls = fetchMock.mock.calls.map((call) => (call as unknown as [string])[0]);
    expect(urls).toEqual([
      '/api/health/db',
      '/api/stats',
      '/api/integrations',
      '/api/ai/provider',
      '/api/tasks/progress',
    ]);
  });
});

describe('api base URL handling', () => {
  it('uses the relative /api path when VITE_API_BASE_URL is empty', async () => {
    vi.stubEnv('VITE_API_BASE_URL', '');
    const fetchMock = stubFetch(() => jsonResponse({ status: 'ok' }));

    await api.getStats();

    expect((fetchMock.mock.calls[0] as unknown as [string])[0]).toBe('/api/stats');
    vi.unstubAllEnvs();
  });

  it('prefixes VITE_API_BASE_URL when it is configured', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://backend.example.test');
    const fetchMock = stubFetch(() => jsonResponse({ status: 'ok' }));

    await api.getStats();

    expect((fetchMock.mock.calls[0] as unknown as [string])[0]).toBe(
      'https://backend.example.test/api/stats',
    );
    vi.unstubAllEnvs();
  });

  it('trims exactly one trailing slash from VITE_API_BASE_URL (no double slash)', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://backend.example.test/');
    const fetchMock = stubFetch(() => jsonResponse({ status: 'ok' }));

    await api.getHealth();

    const url = (fetchMock.mock.calls[0] as unknown as [string])[0];
    expect(url).toBe('https://backend.example.test/api/health');
    expect(url).not.toContain('//api');
    vi.unstubAllEnvs();
  });
});

describe('api unified error template (docs/API.md)', () => {
  it('maps the documented error document to ApiError with status/code/message/details', async () => {
    stubFetch(() => jsonResponse(DOCUMENTED_ERROR, 404));

    const failure = api.getStats();
    await expect(failure).rejects.toBeInstanceOf(ApiError);
    await expect(failure).rejects.toMatchObject({
      status: 404,
      code: 'NOT_FOUND',
      message: 'Resource not found.',
      details: null,
    });
  });

  it('keeps a string `details` value from the documented template', async () => {
    const body = {
      error: { code: 'VALIDATION_ERROR', message: 'Invalid query.', details: 'query: required' },
    };
    stubFetch(() => jsonResponse(body, 422));

    await expect(api.createInvestigation({ query: '', query_type: 'name' })).rejects.toMatchObject({
      status: 422,
      code: 'VALIDATION_ERROR',
      details: 'query: required',
    });
  });

  it('surfaces 401 on protected routes as the documented UNAUTHORIZED code', async () => {
    const body = { error: { code: 'UNAUTHORIZED', message: 'Missing bearer token.', details: null } };
    stubFetch(() => jsonResponse(body, 401));

    const error = await api.getTaskProgress().catch((err: unknown) => err);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 401, code: 'UNAUTHORIZED' });
    // Branching happens on `code`, never on the human-readable message.
    expect((error as ApiError).name).toBe('ApiError');
  });

  it('falls back to UNKNOWN_ERROR when the body does not follow the template', async () => {
    stubFetch(() => jsonResponse({ message: 'plain fastapi error' }, 500));

    await expect(api.getStats()).rejects.toMatchObject({
      status: 500,
      code: 'UNKNOWN_ERROR',
      message: 'Request failed with status 500',
      details: null,
    });
  });

  it('falls back to UNKNOWN_ERROR when an error body is not JSON at all', async () => {
    stubFetch(
      () =>
        new Response('<html>502 Bad Gateway</html>', {
          status: 502,
          headers: { 'Content-Type': 'text/html' },
        }),
    );

    await expect(api.getHealth()).rejects.toMatchObject({
      status: 502,
      code: 'UNKNOWN_ERROR',
    });
  });

  it('turns a network failure into ApiError(0, NETWORK_ERROR) — the documented offline case', async () => {
    stubFetch(() => {
      throw new TypeError('Failed to fetch');
    });

    await expect(api.getHealth()).rejects.toMatchObject({
      status: 0,
      code: 'NETWORK_ERROR',
      message: 'Backend is not reachable',
    });
  });
});

describe('parseApiError', () => {
  it('accepts the documented template', () => {
    const error = parseApiError(404, DOCUMENTED_ERROR);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      status: 404,
      code: 'NOT_FOUND',
      message: 'Resource not found.',
      details: null,
    });
  });

  it('uses safe defaults for a partially-shaped template', () => {
    const error = parseApiError(400, { error: { details: 'only details' } });

    expect(error).toMatchObject({
      status: 400,
      code: 'UNKNOWN_ERROR',
      message: 'Request failed',
      details: 'only details',
    });
  });

  it('uses safe defaults when `error` is not an object', () => {
    expect(parseApiError(500, { error: 'boom' })).toMatchObject({
      status: 500,
      code: 'UNKNOWN_ERROR',
      message: 'Request failed with status 500',
      details: null,
    });
  });

  it('uses safe defaults for a null body', () => {
    expect(parseApiError(503, null)).toMatchObject({
      status: 503,
      code: 'UNKNOWN_ERROR',
    });
  });

  it('never leaks internals: the code is stable snake_case from the template', () => {
    const error = parseApiError(503, {
      error: { code: 'BACKEND_UNAVAILABLE', message: 'Service temporarily down.', details: null },
    });

    expect(error.code).toBe('BACKEND_UNAVAILABLE');
    expect(error.code).toMatch(/^[A-Z][A-Z0-9_]*$/);
  });
});
