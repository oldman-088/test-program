import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach, vi } from 'vitest';

/**
 * Global test setup (task item 21).
 *
 * - Adds the jest-dom matchers (`toBeInTheDocument`, `toHaveAttribute`, …).
 * - Unmounts React trees between tests so the DOM never leaks across files.
 * - Restores stubbed globals (`vi.stubGlobal`) after every test.
 * - Provides a minimal `matchMedia` shim: jsdom does not implement it, and
 *   components/tests that query media queries would otherwise crash.
 *
 * No network access happens here: `fetch` is never called by the setup, every
 * test stubs it explicitly with `vi.stubGlobal('fetch', …)`.
 */

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

if (!window.matchMedia) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    configurable: true,
    value: (query: string): MediaQueryList =>
      ({
        matches: false,
        media: query,
        onchange: null,
        addListener: () => {},
        removeListener: () => {},
        addEventListener: () => {},
        removeEventListener: () => {},
        dispatchEvent: () => false,
      }) as unknown as MediaQueryList,
  });
}
