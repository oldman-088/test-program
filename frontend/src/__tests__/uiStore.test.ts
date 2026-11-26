import { describe, expect, it } from 'vitest';
import { useUiStore } from '../store/uiStore';

describe('uiStore', () => {
  it('defaults to dark theme and English (ltr)', () => {
    const s = useUiStore.getState();
    expect(s.theme).toBe('dark');
    expect(s.locale).toBe('en');
    expect(s.direction).toBe('ltr');
  });

  it('setLocale(ar) flips direction to rtl', () => {
    useUiStore.getState().setLocale('ar');
    expect(useUiStore.getState().direction).toBe('rtl');
    useUiStore.getState().setLocale('en');
    expect(useUiStore.getState().direction).toBe('ltr');
  });

  it('toggleTheme switches dark <-> light', () => {
    useUiStore.getState().setTheme('dark');
    useUiStore.getState().toggleTheme();
    expect(useUiStore.getState().theme).toBe('light');
    useUiStore.getState().toggleTheme();
    expect(useUiStore.getState().theme).toBe('dark');
  });
});
