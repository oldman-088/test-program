import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi, afterEach } from 'vitest';
import { Dashboard } from '../pages/Dashboard';

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('Dashboard', () => {
  it('shows search field, type selector and Start Investigation button', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => Response.json({ error: { code: 'X', message: 'down', details: null } }, { status: 500 })));
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

  it('renders real health data when backend responds', async () => {
    vi.stubGlobal('fetch', vi.fn(async (url: string) => {
      if (url.includes('/api/health/db')) return Response.json({ status: 'ok', database: 'sqlite', latency_ms: 2 });
      if (url.includes('/api/health')) return Response.json({ status: 'ok', version: '0.1.0', timestamp: '2026-01-01T00:00:00Z' });
      if (url.includes('/api/stats')) return Response.json({ total_investigations: 3, total_searches: 10, success_rate: 90, avg_duration_ms: 120 });
      return Response.json({ items: [], total: 0 });
    }));
    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByText('sqlite · 2ms')).toBeInTheDocument());
    await waitFor(() => expect(screen.getByText('3')).toBeInTheDocument());
  });
});
