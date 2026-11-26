import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi, afterEach } from 'vitest';
import { Dashboard } from '../pages/Dashboard';

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('Dashboard', () => {
  it('shows search field, type selector and Start Investigation button', async () => {
    vi.stubGlobal('fetch', vi.fn(async () =>
      Response.json(
        {
          error: {
            code: 'api_error',
            message: 'down',
            details: [],
            request_id: null,
          },
        },
        { status: 500 },
      ),
    ));
    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>,
    );
    expect(screen.getByLabelText('Search query')).toBeInTheDocument();
    expect(screen.getByLabelText('Search type')).toBeInTheDocument();
    expect(screen.getAllByText('Start Investigation').length).toBeGreaterThan(0);
    // Backend down → visible error, never fake data.
    await waitFor(() => expect(screen.getAllByText('down').length).toBeGreaterThan(0));
  });

  it('displays the unified API error code, message, and details when creation fails', async () => {
    const fetchMock = vi.fn(async (_url: string, init?: RequestInit) => {
      if (init?.method === 'POST') {
        return Response.json(
          {
            error: {
              code: 'validation_error',
              message: 'Query was rejected',
              details: [
                {
                  field: 'body.query',
                  loc: ['body', 'query'],
                  message: 'The query is invalid.',
                  type: 'value_error',
                },
              ],
              request_id: 'req-42',
            },
          },
          { status: 400 },
        );
      }
      return Response.json({ items: [], total: 0 });
    });
    vi.stubGlobal('fetch', fetchMock);
    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText('Search query'), { target: { value: 'alice' } });
    fireEvent.click(screen.getByRole('button', { name: 'Start Investigation' }));

    expect(await screen.findByText('validation_error')).toBeInTheDocument();
    expect(await screen.findByText('Query was rejected')).toBeInTheDocument();
    expect(await screen.findByText(/The query is invalid\./)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/investigations',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ query: 'alice', query_type: 'username' }),
      }),
    );
  });

  it('renders real health data when backend responds', async () => {
    vi.stubGlobal('fetch', vi.fn(async (url: string) => {
      if (url.includes('/api/v1/health/ready')) {
        return Response.json({ status: 'ready', database: 'up' });
      }
      if (url.includes('/api/v1/health')) {
        return Response.json({ status: 'ok', version: '0.1.0', environment: 'test' });
      }
      if (url.includes('/api/v1/stats')) {
        return Response.json({ total_investigations: 3, total_searches: 10, success_rate: 90, avg_duration_ms: 120 });
      }
      return Response.json({ items: [], total: 0 });
    }));
    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByText('up')).toBeInTheDocument());
    await waitFor(() => expect(screen.getByText('3')).toBeInTheDocument());
  });
});
