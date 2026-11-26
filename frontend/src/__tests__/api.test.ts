import { describe, expect, it, vi, afterEach } from 'vitest';
import { ApiError, api, parseApiError } from '../lib/api';

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('parseApiError — unified template (docs/API.md)', () => {
  it('parses { error: { code, message, details } }', () => {
    const err = parseApiError(404, {
      error: { code: 'NOT_FOUND', message: 'Missing', details: null },
    });
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(404);
    expect(err.code).toBe('NOT_FOUND');
    expect(err.message).toBe('Missing');
    expect(err.details).toBeNull();
  });

  it('falls back to UNKNOWN_ERROR for non-conforming bodies', () => {
    const err = parseApiError(500, { oops: true });
    expect(err.code).toBe('UNKNOWN_ERROR');
    expect(err.status).toBe(500);
  });
});

describe('api client paths', () => {
  it('getHealth fetches /api/health', async () => {
    const fetchMock = vi.fn(async () =>
      Response.json({ status: 'ok', version: '1.0.0', timestamp: '2026-01-01T00:00:00Z' }),
    );
    vi.stubGlobal('fetch', fetchMock);
    const data = await api.getHealth();
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/api/health'), expect.anything());
    expect(data.status).toBe('ok');
  });

  it('getHealthDb fetches /api/health/db', async () => {
    const fetchMock = vi.fn(async () =>
      Response.json({ status: 'ok', database: 'sqlite', latency_ms: 3 }),
    );
    vi.stubGlobal('fetch', fetchMock);
    const data = await api.getHealthDb();
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/api/health/db'), expect.anything());
    expect(data.database).toBe('sqlite');
  });

  it('throws ApiError with NETWORK_ERROR when fetch rejects', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new Error('down'); }));
    await expect(api.getHealth()).rejects.toMatchObject({ code: 'NETWORK_ERROR', status: 0 });
  });

  it('throws ApiError from unified template on HTTP error', async () => {
    vi.stubGlobal('fetch', vi.fn(async () =>
      Response.json({ error: { code: 'UNAUTHORIZED', message: 'No auth', details: null } }, { status: 401 }),
    ));
    await expect(api.getStats()).rejects.toMatchObject({ code: 'UNAUTHORIZED', status: 401 });
  });

  it('createInvestigation POSTs to /api/investigations with query_type', async () => {
    const fetchMock = vi.fn(async () =>
      Response.json(
        { id: '1', query: 'alice', query_type: 'username', status: 'queued', created_at: '2026-01-01T00:00:00Z' },
        { status: 201 },
      ),
    );
    vi.stubGlobal('fetch', fetchMock);
    await api.createInvestigation({ query: 'alice', query_type: 'username' });
    const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body as string)).toEqual({ query: 'alice', query_type: 'username' });
  });
});
