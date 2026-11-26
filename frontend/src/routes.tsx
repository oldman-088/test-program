import { createBrowserRouter } from 'react-router-dom';
import { AppLayout } from './components/layout/AppLayout';
import { Dashboard } from './pages/Dashboard';
import { Placeholder } from './pages/Placeholder';

export const router = createBrowserRouter([
  {
    path: '/',
    element: (
      <AppLayout>
        <Dashboard />
      </AppLayout>
    ),
  },
  {
    path: '/investigations/new',
    element: (
      <AppLayout>
        <Placeholder titleKey="nav.newInvestigation" />
      </AppLayout>
    ),
  },
  {
    path: '/investigations/history',
    element: (
      <AppLayout>
        <Placeholder titleKey="nav.investigationHistory" />
      </AppLayout>
    ),
  },
  {
    path: '/search-tools',
    element: (
      <AppLayout>
        <Placeholder titleKey="nav.searchTools" />
      </AppLayout>
    ),
  },
  {
    path: '/results',
    element: (
      <AppLayout>
        <Placeholder titleKey="nav.results" />
      </AppLayout>
    ),
  },
  {
    path: '/graph',
    element: (
      <AppLayout>
        <Placeholder titleKey="nav.relationshipGraph" />
      </AppLayout>
    ),
  },
  {
    path: '/timeline',
    element: (
      <AppLayout>
        <Placeholder titleKey="nav.timeline" />
      </AppLayout>
    ),
  },
  {
    path: '/reports',
    element: (
      <AppLayout>
        <Placeholder titleKey="nav.reports" />
      </AppLayout>
    ),
  },
  {
    path: '/integrations',
    element: (
      <AppLayout>
        <Placeholder titleKey="nav.integrations" />
      </AppLayout>
    ),
  },
  {
    path: '/settings',
    element: (
      <AppLayout>
        <Placeholder titleKey="nav.settings" />
      </AppLayout>
    ),
  },
  {
    path: '/about',
    element: (
      <AppLayout>
        <Placeholder titleKey="nav.about" />
      </AppLayout>
    ),
  },
  {
    path: '*',
    element: (
      <AppLayout>
        <Placeholder />
      </AppLayout>
    ),
  },
]);
