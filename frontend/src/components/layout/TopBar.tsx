import { useLocale } from '../../hooks/useLocale';
import { useUiStore } from '../../store/uiStore';
import { Button } from '../ui/button';
import { Select } from '../ui/select';
import type { Locale } from '../../lib/i18n';

export function TopBar() {
  const { locale, t, setLocale } = useLocale();
  const theme = useUiStore((s) => s.theme);
  const toggleTheme = useUiStore((s) => s.toggleTheme);

  return (
    <header className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
      <p className="text-sm font-semibold">{t('app.name')}</p>
      <div className="flex items-center gap-2">
        <label htmlFor="locale-select" className="sr-only">
          {t('a11y.language')}
        </label>
        <Select
          id="locale-select"
          aria-label={t('a11y.language')}
          value={locale}
          onChange={(e) => setLocale(e.target.value as Locale)}
          className="h-9 w-auto"
        >
          <option value="en">{t('settings.english')}</option>
          <option value="ar">{t('settings.arabic')}</option>
        </Select>
        <Button
          variant="outline"
          size="sm"
          onClick={toggleTheme}
          aria-label={t('a11y.theme')}
          aria-pressed={theme === 'light'}
        >
          {theme === 'dark' ? t('settings.light') : t('settings.dark')}
        </Button>
      </div>
    </header>
  );
}
