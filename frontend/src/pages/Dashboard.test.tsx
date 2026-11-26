import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { Dashboard } from './Dashboard';

/**
 * Dashboard behaviour against a mocked `fetch` (no real backend, no network).
 *
 * Three states are covered:
 *  - success: rendered data comes from the documented endpoints
 *  - loading: the loading skeletons are shown while requests are in flight
 *  - error:   a failing /api/health request shows the visible error state
 *             instead of fake data (docs/API.md: "لا تُعرض أي بيانات وهمية").
 */

const HEALTH_OK = { status: 'ok', version: '0.1.0', timestamp: '2026-11-26T00:00:00Z' };
const HEALTH_DB_OK = { status: 'ok', database: 'sqlite', latency_ms: 2 };
const STATS_OK = {
  total_investigations: 7,
  total_searches: 21,
  success_rate: 92,
  avg_duration_ms: 120,
};
const RECENT_OK = {
  items: [
    {
      id: 'inv-1',
      query: 'alice_target',
      query_type: 'username',
      status: 'completed',
      created_at: '2026-11-26T00:00:00Z',
    },
  ],
  total: 1,
};
const INTEGRATIONS_OK = {
  items: [{ id: 'sherlock', name: 'Sherlock', status: 'available', description: 'Username search' }],
};
const AI_OK = { provider: 'ollama', model: 'llama3', status: 'available', latency_ms: 42 };
const TASKS_OK = { items: [{ id: 't-1', name: 'OSINT sweep', status: 'running', progress: 40 }], total: 1 };
const REPORTS_OK = {
  items: [
    { id: 'r-1', title: 'Quarterly finding', status: 'ready', created_at: '2026-11-26T00:00:00Z' },
  ],
  total: 1,
};

/**
 * Build a *fresh* `Response` per call: a Response body can only be read once,
 * and the dashboard re-fetches sections after starting an investigation.
 */
function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

/** Route handlers are called once per request so every call gets a fresh body. */
type RouteHandler = () => Response;

/** Route the mocked fetch by the documented path (docs/API.md §1–9). */
function stubBackend(overrides: Record<string, RouteHandler> = {}) {
  const routes: Record<string, RouteHandler> = {
    '/api/health/db': () => json(HEALTH_DB_OK),
    '/api/health': () => json(HEALTH_OK),
    '/api/investigations/recent': () => json(RECENT_OK),
    '/api/stats': () => json(STATS_OK),
    '/api/integrations': () => json(INTEGRATIONS_OK),
    '/api/ai/provider': () => json(AI_OK),
    '/api/tasks/progress': () => json(TASKS_OK),
    '/api/reports/latest': () => json(REPORTS_OK),
    ...overrides,
  };
  // Longest path first so /api/health/db is not shadowed by /api/health.
  const paths = Object.keys(routes).sort((a, b) => b.length - a.length);

  // Two declared parameters keep `mock.calls[n]` typed as [url, init] so the
  // POST assertions can read the request body.
  const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit) => {
    const url = String(input);
    const key = paths.find((path) => url.startsWith(path));
    if (!key) throw new Error(`Unexpected fetch in test: ${url}`);
    return routes[key]();
  });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

function renderDashboard() {
  return render(
    <MemoryRouter>
      <Dashboard />
    </MemoryRouter>,
  );
}

describe('Dashboard — rendered content', () => {
  it('renders the page title, search form and all dashboard sections', async () => {
    stubBackend();
    renderDashboard();

    expect(screen.getByRole('heading', { name: 'NEXUS OSINT' })).toBeInTheDocument();
    expect(screen.getByLabelText('Search query')).toBeInTheDocument();
    expect(screen.getByLabelText('Search type')).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Start Investigation' }),
    ).toBeInTheDocument();

    for (const title of [
      'Backend status',
      'Start Investigation',
      'Recent investigations',
      'Available integrations',
      'AI provider status',
      'Task progress',
      'Latest reports',
    ]) {
      expect(screen.getAllByText(title).length).toBeGreaterThan(0);
    }

    // Grouping is exposed to assistive tech, not just visually.
    expect(screen.getByRole('combobox', { name: 'Search type' })).toHaveValue('username');
    expect(
      screen.getByRole('option', { name: 'Username' }),
    ).toBeInTheDocument();
  });

  it('renders the real data returned by the documented endpoints', async () => {
    stubBackend();
    renderDashboard();

    // Health + DB (§1–2)
    expect(await screen.findByText('sqlite · 2ms')).toBeInTheDocument();
    expect(screen.getByText('v0.1.0')).toBeInTheDocument();

    // Recent investigations (§3) and stats (§4)
    expect(await screen.findByText('alice_target')).toBeInTheDocument();
    expect(screen.getByText('7')).toBeInTheDocument();
    expect(screen.getByText('21')).toBeInTheDocument();

    // Integrations (§5)
    expect(await screen.findByText('Sherlock')).toBeInTheDocument();
    expect(screen.getAllByText('available').length).toBeGreaterThan(0);

    // AI provider (§6)
    expect(await screen.findByText('ollama')).toBeInTheDocument();
    expect(screen.getByText('llama3')).toBeInTheDocument();

    // Task progress (§7) — exposed as a real progressbar with its value
    const progressbar = await screen.findByRole('progressbar', { name: 'OSINT sweep' });
    expect(progressbar).toHaveAttribute('aria-valuenow', '40');
    expect(progressbar).toHaveAttribute('aria-valuemin', '0');
    expect(progressbar).toHaveAttribute('aria-valuemax', '100');

    // Latest reports (§8)
    expect(await screen.findByText('Quarterly finding')).toBeInTheDocument();
  });

  it('shows empty states instead of fake rows when collections are empty', async () => {
    stubBackend({
      '/api/investigations/recent': () => json({ items: [], total: 0 }),
      '/api/reports/latest': () => json({ items: [], total: 0 }),
    });
    renderDashboard();

    const emptyMessage = 'No data available yet. Start an investigation to see results here.';
    await waitFor(() =>
      expect(screen.getAllByText(emptyMessage).length).toBeGreaterThanOrEqual(2),
    );
    expect(screen.queryByText('alice_target')).not.toBeInTheDocument();
  });
});

describe('Dashboard — loading state', () => {
  it('shows loading skeletons while the requests are still in flight', () => {
    // A fetch that never settles keeps every section in its loading state.
    vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(() => {})));

    renderDashboard();

    // The health card renders its skeleton block (aria-label="Loading").
    const healthSkeleton = screen
      .getAllByLabelText('Loading')
      .find((node) => node.tagName === 'DIV');
    expect(healthSkeleton).toBeInTheDocument();
    // Many sections → many skeletons; none of them are rows of fake data.
    expect(screen.getAllByLabelText('Loading').length).toBeGreaterThan(1);
    expect(screen.queryByText('sqlite · 2ms')).not.toBeInTheDocument();
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
    // Errors are never shown while a request is merely pending.
    expect(screen.queryByText('Backend is not reachable')).not.toBeInTheDocument();
  });

  it('replaces the skeletons with data once the backend answers', async () => {
    stubBackend();
    renderDashboard();

    expect(await screen.findByText('sqlite · 2ms')).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByLabelText('Loading')).not.toBeInTheDocument());
  });
});

describe('Dashboard — error state', () => {
  it('shows the visible error state when GET /api/health fails (documented error template)', async () => {
    stubBackend({
      '/api/health': () =>
        json(
          {
            error: {
              code: 'BACKEND_UNAVAILABLE',
              message: 'Backend is not reachable',
              details: null,
            },
          },
          503,
        ),
    });

    renderDashboard();

    // role="alert" makes the failure announceable, and the unified-template
    // message is shown verbatim instead of fake health data.
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Backend is not reachable');

    expect(screen.queryByText('v0.1.0')).not.toBeInTheDocument();
    expect(screen.queryByText('sqlite · 2ms')).not.toBeInTheDocument();
    // The retry affordance stays available.
    expect(within(alert).getByRole('button', { name: 'Retry' })).toBeInTheDocument();
  });

  it('shows the error state when the health request cannot reach the network at all', async () => {
    stubBackend({
      '/api/health': () => {
        throw new TypeError('Failed to fetch');
      },
    });

    renderDashboard();

    // The client maps a rejected fetch to ApiError(0, NETWORK_ERROR) with this
    // fixed message (docs/API.md offline case) — not the generic i18n fallback.
    const networkAlert = await screen.findByRole('alert');
    expect(networkAlert).toHaveTextContent('Backend is not reachable');
    expect(networkAlert).not.toHaveTextContent('Check that the API server is running');
    expect(screen.queryByText('sqlite · 2ms')).not.toBeInTheDocument();
  });

  it('recovers after a retry when the backend comes back', async () => {
    let healthy = false;
    stubBackend({
      '/api/health': () =>
        healthy
          ? json(HEALTH_OK)
          : json(
              { error: { code: 'BACKEND_UNAVAILABLE', message: 'Backend is down', details: null } },
              503,
            ),
    });

    renderDashboard();

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Backend is down');

    healthy = true;
    fireEvent.click(within(alert).getByRole('button', { name: 'Retry' }));

    expect(await screen.findByText('v0.1.0')).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText('Backend is down')).not.toBeInTheDocument());
  });

  it('keeps the health card healthy while an unrelated section fails', async () => {
    stubBackend({
      '/api/stats': () =>
        json({ error: { code: 'INTERNAL_ERROR', message: 'stats exploded', details: null } }, 500),
    });

    renderDashboard();

    expect(await screen.findByText('v0.1.0')).toBeInTheDocument();
    expect(await screen.findByText('stats exploded')).toBeInTheDocument();
    // A section-level failure must not blank the whole dashboard.
    expect(screen.getByText('sqlite · 2ms')).toBeInTheDocument();
  });
});

describe('Dashboard — starting an investigation', () => {
  it('validates an empty query locally without calling the API', async () => {
    const fetchMock = stubBackend();
    renderDashboard();

    await screen.findByText('sqlite · 2ms');
    const callsBefore = fetchMock.mock.calls.length;

    fireEvent.click(screen.getByRole('button', { name: 'Start Investigation' }));

    expect(await screen.findByText('Enter a search query first')).toBeInTheDocument();
    expect(screen.getByLabelText('Search query')).toHaveAttribute('aria-invalid', 'true');
    expect(fetchMock.mock.calls.length).toBe(callsBefore);
  });

  it('POSTs the query and shows the queued confirmation', async () => {
    const fetchMock = stubBackend({
      '/api/investigations': () =>
        json(
          {
            id: 'inv-2',
            query: 'alice',
            query_type: 'username',
            status: 'queued',
            created_at: '2026-11-26T00:00:00Z',
          },
          201,
        ),
    });
    renderDashboard();

    await screen.findByText('sqlite · 2ms');
    fireEvent.change(screen.getByLabelText('Search query'), { target: { value: '  alice  ' } });
    fireEvent.click(screen.getByRole('button', { name: 'Start Investigation' }));

    expect(await screen.findByRole('status')).toHaveTextContent('Investigation queued');

    const postCall = fetchMock.mock.calls.find(
      (call) => (call[1] as RequestInit | undefined)?.method === 'POST',
    ) as unknown as [string, RequestInit];
    expect(postCall[0]).toBe('/api/investigations');
    expect(JSON.parse(postCall[1].body as string)).toEqual({
      query: 'alice', // trimmed
      query_type: 'username',
    });
  });

  it('shows a visible error when POST /api/investigations fails', async () => {
    stubBackend({
      '/api/investigations': () =>
        json({ error: { code: 'VALIDATION_ERROR', message: 'Query rejected', details: null } }, 422),
    });
    renderDashboard();

    await screen.findByText('sqlite · 2ms');
    fireEvent.change(screen.getByLabelText('Search query'), { target: { value: 'alice' } });
    fireEvent.click(screen.getByRole('button', { name: 'Start Investigation' }));

    expect(await screen.findByText('Query rejected')).toBeInTheDocument();
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });
});
