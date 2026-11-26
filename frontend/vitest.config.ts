import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

/**
 * Dedicated Vitest configuration for the frontend test layer (task item 21).
 *
 * Kept separate from `vite.config.ts` so that the dev server / production
 * build configuration stays untouched and tests always run in `jsdom` with the
 * shared setup file. There is no `server`/`proxy` block here on purpose:
 * every test replaces `fetch` with a mock, so no test may reach the network.
 *
 * Run with: `npm run test` (or `npm run test:watch` while developing).
 */
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: false,
    restoreMocks: true,
    clearMocks: true,
    // Tests must never depend on an external service.
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    testTimeout: 10_000,
  },
});
