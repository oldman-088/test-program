import { describe, expect, it, vi, afterEach } from 'vitest';
import { ApiError, api, parseApiError } from '../lib/api';

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('parseApiError — unified template (docs/API.md, main)', () => {
  it('parses { error: { code, message, details, request_id } }', () => {
    const err = parseApiError(404, {
      error: {
        code: 'not_found',
        message: 'Missing',
        details: [],
        request_id: '6f1d2c4a8b9e4f70a1b2c3d4e5f60718',
      },
    });
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(404);
    expect(err.code).toBe('not_found');
    expect(err.message).toBe('Missing');
    expect(err.details).toEqual([]);
    expect(err.requestId).toBe('6f1d2c4a8b9e4f70a1b2c3d4e5f60718');
  });

  it('parses validation details as an array of objects', () => {
    const err = parseApiError(422, {
      error: {
        code: 'validation_error',
        message: 'تحقق واحد على الأقل فشل (1).',
        details: [
          {
            field: 'body.task_id',
            loc: ['body', 'task_id'],
            message: 'String should have at least 8 characters',
            type: 'string_too_short',
          },
        ],
        request_id: null,
      },
    });
    expect(err.code).toBe('validation_error');
    expect(err.details).toHaveLength(1);
    expect(err.details[0]).toMatchObject({ field: 'body.task_id', type: 'string_too_short' });
    expect(err.requestId).toBeNull();
  });

  it('falls back to UNKNOWN_ERROR for non-conforming bodies', () => {
    const err = parseApiError(500, { oops: true });
    expect(err.code).toBe('UNKNOWN_ERROR');
    expect(err.status).toBe(500);
  });
});

describe('api client paths and auth (contract)', () => {
  it('getHealth fetches the public /api/v1/health without X-API-Key', async () => {
    const fetchMock = vi.fn(async (_url: string, init?: RequestInit) => {
      expect(_url).toContain('/api/v1/health');
      expect(init?.headers).not.toHaveProperty('X-API-Key');
      return Response.json({ status: 'ok', version: '1.0.0', environment: 'test' });
    });
    vi.stubGlobal('fetch', fetchMock);
    const data = await api.getHealth();
    expect(data.status).toBe('ok');
    expect(data.environment).toBe('test');
  });

  it('getHealthReady fetches the public /api/v1/health/ready without X-API-Key', async () => {
    const fetchMock = vi.fn(async (_url: string, init?: RequestInit) => {
      expect(_url).toContain('/api/v1/health/ready');
      expect(init?.headers).not.toHaveProperty('X-API-Key');
      return Response.json({ status: 'ready', database: 'up' });
    });
    vi.stubGlobal('fetch', fetchMock);
    const data = await api.getHealthReady();
    expect(data.status).toBe('ready');
    expect(data.database).toBe('up');
  });

  it('sends X-API-Key from VITE_API_KEY on protected endpoints', async () => {
    vi.stubEnv('VITE_API_KEY', 'test-key-123');
    const fetchMock = vi.fn(async (_url: string, init?: RequestInit) => {
      expect(_url).toContain('/api/v1/stats');
      expect((init?.headers as Record<string, string>)['X-API-Key']).toBe('test-key-123');
      return Response.json({
        total_investigations: 0,
        total_searches: 0,
        success_rate: 0,
        avg_duration_ms: 0,
      });
    });
    vi.stubGlobal('fetch', fetchMock);
    await api.getStats();
  });

  it('throws ApiError with NETWORK_ERROR when fetch rejects', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new Error('down'); }));
    await expect(api.getHealth()).rejects.toMatchObject({ code: 'NETWORK_ERROR', status: 0 });
  });

  it('throws ApiError from the unified template on HTTP error', async () => {
    vi.stubGlobal('fetch', vi.fn(async () =>
      Response.json(
        {
          error: {
            code: 'unauthenticated',
            message: 'No auth',
            details: [],
            request_id: 'req-1',
          },
        },
        { status: 401 },
      ),
    ));
    await expect(api.getStats()).rejects.toMatchObject({ code: 'unauthenticated', status: 401 });
  });

  it('createInvestigation matches the documented POST path, request, and response', async () => {
    const responseBody = {
      id: '1',
      query: 'alice',
      query_type: 'username',
      status: 'queued',
      created_at: '2026-01-01T00:00:00Z',
    };
    const fetchMock = vi.fn(async (_url: string, init?: RequestInit) => {
      expect(_url).toBe('/api/v1/investigations');
      expect(init?.method).toBe('POST');
      return Response.json(responseBody, { status: 201 });
    });
    vi.stubGlobal('fetch', fetchMock);

    const result = await api.createInvestigation({ query: 'alice', query_type: 'username' });

    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe('/api/v1/investigations');
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body as string)).toEqual({ query: 'alice', query_type: 'username' });
    expect(result).toEqual(responseBody);
  });
});
