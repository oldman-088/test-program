import { useUiStore } from '../store/uiStore';
import { createTranslator, type Locale } from '../lib/i18n';

/**
 * Returns the active locale, a `t(key)` translator bound to it, and setters.
 * Switching locale flips the whole UI and (via useDirection) the page direction.
 */
export function useLocale() {
  const locale = useUiStore((s) => s.locale) as Locale;
  const setLocale = useUiStore((s) => s.setLocale);
  const t = createTranslator(locale);
  return { locale, t, setLocale };
}
