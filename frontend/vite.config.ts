import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Dev proxy: relative /api requests from the browser are forwarded to the
// backend so `frontend/src/` never hardcodes localhost/127.0.0.1.
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test-setup.ts'],
  },
});
