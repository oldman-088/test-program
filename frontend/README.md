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

The dashboard reads real endpoints from the fixed contract in `docs/API.md`
(main) — all under the `/api/v1` prefix: `/api/v1/health` and
`/api/v1/health/ready` (public, no auth), plus `/api/v1/investigations/recent`,
`/api/v1/stats`, `/api/v1/integrations`, `/api/v1/ai/provider`,
`/api/v1/tasks/progress`, `/api/v1/reports/latest` and
`POST /api/v1/investigations` via `src/lib/api.ts`. Protected endpoints send
the `X-API-Key` header from `VITE_API_KEY` (see `.env.example`). When the
backend is down it shows the unified-template error — never fake data.
