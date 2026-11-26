import { NavLink } from 'react-router-dom';
import { useLocale } from '../../hooks/useLocale';
import { cn } from '../../lib/utils';

/**
 * Sidebar — exactly these 11 items, in this order, each with a route.
 * Labels come from locales (en/ar) so the whole nav flips with language.
 */
export const NAV_ITEMS = [
  { key: 'nav.dashboard', path: '/' },
  { key: 'nav.newInvestigation', path: '/investigations/new' },
  { key: 'nav.investigationHistory', path: '/investigations/history' },
  { key: 'nav.searchTools', path: '/search-tools' },
  { key: 'nav.results', path: '/results' },
  { key: 'nav.relationshipGraph', path: '/graph' },
  { key: 'nav.timeline', path: '/timeline' },
  { key: 'nav.reports', path: '/reports' },
  { key: 'nav.integrations', path: '/integrations' },
  { key: 'nav.settings', path: '/settings' },
  { key: 'nav.about', path: '/about' },
] as const;

export function Sidebar() {
  const { t } = useLocale();

  return (
    <nav aria-label={t('a11y.mainNavigation')} className="flex h-full flex-col">
      <div className="px-4 py-5">
        <p className="text-lg font-bold tracking-tight">{t('app.name')}</p>
        <p className="text-xs text-muted-foreground">{t('app.tagline')}</p>
      </div>
      <ul className="flex-1 space-y-1 px-3">
        {NAV_ITEMS.map((item) => (
          <li key={item.path}>
            <NavLink
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) =>
                cn(
                  'block rounded-md px-3 py-2 text-sm font-medium transition-colors',
                  'hover:bg-accent hover:text-accent-foreground',
                  isActive && 'bg-primary text-primary-foreground hover:bg-primary',
                )
              }
            >
              {t(item.key)}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
