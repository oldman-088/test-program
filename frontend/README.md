# NEXUS OSINT — Frontend

Vite + React + TypeScript dashboard (dark by default, EN/AR with LTR/RTL).

## Run

```bash
cd frontend
cp .env.example .env.local   # optional; leave VITE_API_BASE_URL empty for relative /api
npm install
npm run dev                  # http://localhost:3000 (proxies /api to :8000)
npm run build                # type-check + production build
npm test                     # vitest
```

The dashboard reads real endpoints from `docs/API.md` (`/api/health`,
`/api/health/db`, `/api/investigations/recent`, `/api/stats`,
`/api/integrations`, `/api/ai/provider`, `/api/tasks/progress`,
`/api/reports/latest`) via `src/lib/api.ts`. When the backend is down it
shows the unified-template error — never fake data.

## Tests (بند 21 — frontend test layer)

Vitest + Testing Library in a `jsdom` environment. No test touches a real
network or a paid service: every request goes through `vi.stubGlobal('fetch', …)`.

```bash
cd frontend
npm test           # vitest run — all suites, once
npm run test:watch # watch mode while developing
```

| File | Covers |
|---|---|
| `vitest.config.ts` | jsdom environment, shared setup, `src/**/*.test.{ts,tsx}` |
| `src/test/setup.ts` | jest-dom matchers, cleanup between tests, `matchMedia` shim |
| `src/components/ui/button.test.tsx` | click/keyboard behaviour, `disabled`, `aria-busy`, accessible names, variants |
| `src/lib/api.test.ts` | request building, `VITE_API_BASE_URL` handling, unified error template from `docs/API.md`, `fetch` mocked |
| `src/store/uiStore.test.ts` | theme switching, language switching, `<html dir/lang>` page direction (ltr/rtl) |
| `src/pages/Dashboard.test.tsx` | rendered sections, loading skeletons, health-failure error state, retry, investigation submit |
