import en from './locales/en.json';
import ar from './locales/ar.json';

export type Locale = 'en' | 'ar';
export type Direction = 'ltr' | 'rtl';

export const SUPPORTED_LOCALES: Locale[] = ['en', 'ar'];

const dictionaries: Record<Locale, Record<string, unknown>> = {
  en: en as Record<string, unknown>,
  ar: ar as Record<string, unknown>,
};

/** Direction for a locale: Arabic is RTL, English is LTR. */
export function directionForLocale(locale: Locale): Direction {
  return locale === 'ar' ? 'rtl' : 'ltr';
}

function lookup(dict: Record<string, unknown>, key: string): string | undefined {
  const parts = key.split('.');
  let node: unknown = dict;
  for (const part of parts) {
    if (node === null || typeof node !== 'object') return undefined;
    node = (node as Record<string, unknown>)[part];
  }
  return typeof node === 'string' ? node : undefined;
}

/**
 * Translate a dotted key (e.g. `nav.dashboard`) for a locale.
 * Falls back to English, then to the key itself — never throws.
 */
export function translate(locale: Locale, key: string): string {
  return (
    lookup(dictionaries[locale], key) ??
    lookup(dictionaries.en, key) ??
    key
  );
}

/** Type-safe-ish `t` factory bound to a locale. */
export function createTranslator(locale: Locale) {
  return (key: string) => translate(locale, key);
}
