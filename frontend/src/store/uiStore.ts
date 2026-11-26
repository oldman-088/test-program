import { create } from 'zustand';
import type { Direction, Locale } from '../lib/i18n';
import { directionForLocale } from '../lib/i18n';

export type Theme = 'dark' | 'light';

interface UiState {
  locale: Locale;
  theme: Theme;
  direction: Direction;
  setLocale: (locale: Locale) => void;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
}

/**
 * Global UI store: language, theme (dark by default) and page direction.
 * Direction is derived from locale (ar → rtl, en → ltr) and kept in sync here
 * so hooks/components can read it without recomputing.
 */
export const useUiStore = create<UiState>((set) => ({
  locale: 'en',
  theme: 'dark',
  direction: directionForLocale('en'),
  setLocale: (locale) =>
    set({ locale, direction: directionForLocale(locale) }),
  setTheme: (theme) => set({ theme }),
  toggleTheme: () =>
    set((state) => ({ theme: state.theme === 'dark' ? 'light' : 'dark' })),
}));
