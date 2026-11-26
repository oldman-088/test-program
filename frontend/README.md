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
