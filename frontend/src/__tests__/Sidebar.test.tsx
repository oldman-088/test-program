import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { NAV_ITEMS, Sidebar } from '../components/layout/Sidebar';

describe('Sidebar', () => {
  it('renders exactly the 11 required items in order, each with a path', () => {
    expect(NAV_ITEMS).toHaveLength(11);
    expect(NAV_ITEMS.map((i) => i.path)).toEqual([
      '/',
      '/investigations/new',
      '/investigations/history',
      '/search-tools',
      '/results',
      '/graph',
      '/timeline',
      '/reports',
      '/integrations',
      '/settings',
      '/about',
    ]);

    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>,
    );
    const links = screen.getAllByRole('link');
    expect(links).toHaveLength(11);
    expect(links[0]).toHaveTextContent('Dashboard');
    expect(links[10]).toHaveTextContent('About');
  });
});
