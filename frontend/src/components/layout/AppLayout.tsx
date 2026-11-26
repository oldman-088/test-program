import type { ReactNode } from 'react';
import { useLocale } from '../../hooks/useLocale';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';

export function AppLayout({ children }: { children: ReactNode }) {
  const { t } = useLocale();

  return (
    <div className="flex min-h-screen bg-background text-foreground">
      {/* Logical properties (ms-/me-/ps-/pe-) keep LTR/RTL parity. */}
      <aside className="hidden w-64 shrink-0 border-e border-border md:block">
        <Sidebar />
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        {/* Mobile nav: same 11 items, horizontally scrollable. */}
        <div className="border-b border-border md:hidden">
          <Sidebar />
        </div>
        <main id="main-content" className="flex-1 p-4 md:p-6" tabIndex={-1}>
          <a
            href="#main-content"
            className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:bg-primary focus:px-3 focus:py-2 focus:text-primary-foreground"
          >
            {t('a11y.skipToContent')}
          </a>
          {children}
        </main>
      </div>
    </div>
  );
}
