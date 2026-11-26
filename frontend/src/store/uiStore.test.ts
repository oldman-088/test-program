import { act, render, screen } from '@testing-library/react';
import { createElement } from 'react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';
import { TopBar } from '../components/layout/TopBar';
import { useDirection } from '../hooks/useDirection';
import { useUiStore } from './uiStore';

/**
 * `uiStore` contract: theme switching, language switching and the page
 * direction (rtl for Arabic, ltr for English) that follows the language.
 *
 * This file is plain TypeScript (no JSX) by design — it is imported through
 * `createElement` so it keeps the `.ts` path from the task spec while still
 * rendering real components.
 */

function DirectionProbe() {
  // useDirection applies dir/lang to <html> as a side effect and returns it.
  const direction = useDirection();
  return createElement('output', { 'data-testid': 'direction' }, direction);
}

const INITIAL_STATE = { locale: 'en', theme: 'dark', direction: 'ltr' } as const;

beforeEach(() => {
  // Tests are order-independent: always start from the documented defaults.
  act(() => {
    useUiStore.setState({ ...INITIAL_STATE });
  });
  document.documentElement.removeAttribute('dir');
  document.documentElement.removeAttribute('lang');
  document.documentElement.classList.remove('dark', 'light');
});

describe('uiStore defaults', () => {
  it('starts in dark theme, English and ltr direction', () => {
    const state = useUiStore.getState();

    expect(state.theme).toBe('dark');
    expect(state.locale).toBe('en');
    expect(state.direction).toBe('ltr');
  });
});

describe('uiStore theme switching', () => {
  it('setTheme switches the theme explicitly', () => {
    act(() => useUiStore.getState().setTheme('light'));
    expect(useUiStore.getState().theme).toBe('light');

    act(() => useUiStore.getState().setTheme('dark'));
    expect(useUiStore.getState().theme).toBe('dark');
  });

  it('toggleTheme flips dark → light → dark and leaves lang/direction alone', () => {
    const before = useUiStore.getState();

    act(() => useUiStore.getState().toggleTheme());
    expect(useUiStore.getState().theme).toBe('light');

    act(() => useUiStore.getState().toggleTheme());
    expect(useUiStore.getState().theme).toBe('dark');

    expect(useUiStore.getState().locale).toBe(before.locale);
    expect(useUiStore.getState().direction).toBe('ltr');
  });

  it('switching the theme from the TopBar updates the store and aria-pressed', async () => {
    const user = userEvent.setup();
    render(createElement(TopBar));

    const themeButton = screen.getByRole('button', { name: 'Theme' });
    expect(themeButton).toHaveAttribute('aria-pressed', 'false');
    expect(themeButton).toHaveTextContent('Light');

    await user.click(themeButton);

    expect(useUiStore.getState().theme).toBe('light');
    expect(screen.getByRole('button', { name: 'Theme' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    expect(screen.getByRole('button', { name: 'Theme' })).toHaveTextContent('Dark');
  });
});

describe('uiStore language and page direction', () => {
  it('setLocale("ar") switches to Arabic and flips the page direction to rtl', () => {
    act(() => useUiStore.getState().setLocale('ar'));

    const state = useUiStore.getState();
    expect(state.locale).toBe('ar');
    expect(state.direction).toBe('rtl');
  });

  it('setLocale("en") goes back to English and ltr', () => {
    act(() => useUiStore.getState().setLocale('ar'));
    act(() => useUiStore.getState().setLocale('en'));

    const state = useUiStore.getState();
    expect(state.locale).toBe('en');
    expect(state.direction).toBe('ltr');
  });

  it('writes dir/lang onto <html> and re-renders the hook consumer', () => {
    render(createElement(DirectionProbe));

    expect(screen.getByTestId('direction')).toHaveTextContent('ltr');
    expect(document.documentElement).toHaveAttribute('dir', 'ltr');
    expect(document.documentElement).toHaveAttribute('lang', 'en');

    act(() => useUiStore.getState().setLocale('ar'));

    expect(screen.getByTestId('direction')).toHaveTextContent('rtl');
    expect(document.documentElement).toHaveAttribute('dir', 'rtl');
    expect(document.documentElement).toHaveAttribute('lang', 'ar');

    act(() => useUiStore.getState().setLocale('en'));

    expect(document.documentElement).toHaveAttribute('dir', 'ltr');
    expect(document.documentElement).toHaveAttribute('lang', 'en');
  });

  it('changing the language from the TopBar flips direction and translates its labels', async () => {
    const user = userEvent.setup();
    render(
      createElement(
        'div',
        null,
        createElement(TopBar),
        createElement(DirectionProbe),
      ),
    );

    const languageSelect = screen.getByRole('combobox', { name: 'Language' });
    expect(languageSelect).toHaveValue('en');

    await user.selectOptions(languageSelect, 'ar');

    expect(useUiStore.getState().locale).toBe('ar');
    expect(useUiStore.getState().direction).toBe('rtl');
    expect(screen.getByTestId('direction')).toHaveTextContent('rtl');
    expect(document.documentElement).toHaveAttribute('dir', 'rtl');
    // Accessible names come from the Arabic dictionary now.
    expect(screen.getByRole('combobox', { name: 'اللغة' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'السمة' })).toBeInTheDocument();
  });

  it('keeps the theme untouched when only the language changes', () => {
    act(() => useUiStore.getState().setTheme('light'));
    act(() => useUiStore.getState().setLocale('ar'));

    expect(useUiStore.getState().theme).toBe('light');
    expect(useUiStore.getState().direction).toBe('rtl');
  });
});
