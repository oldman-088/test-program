import { describe, expect, it } from 'vitest';
import { directionForLocale, translate } from '../lib/i18n';

describe('i18n', () => {
  it('translates nav labels in English and Arabic', () => {
    expect(translate('en', 'nav.dashboard')).toBe('Dashboard');
    expect(translate('ar', 'nav.dashboard')).toBe('لوحة القيادة');
    expect(translate('en', 'nav.about')).toBe('About');
    expect(translate('ar', 'nav.about')).toBe('حول');
  });

  it('falls back to English then to the key', () => {
    expect(translate('ar', 'missing.key')).toBe('missing.key');
  });

  it('maps locales to directions', () => {
    expect(directionForLocale('ar')).toBe('rtl');
    expect(directionForLocale('en')).toBe('ltr');
  });
});
