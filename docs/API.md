# Backend API Contract — `docs/API.md`

> **Single source of truth** for the HTTP API contract of this project. The dashboard frontend
> must comply with this document **literally**.
>
> **Owner:** Worker 1 — Backend Lead (sole maintainer of this file in this plan).
> Any new or changed endpoint must be documented here **in the same pull request** that
> implements it. If code and this file disagree, the code is wrong.

- Stack: FastAPI with Pydantic v2.
- OpenAPI document: `GET /api/openapi.json` · Swagger UI: `/api/docs` · ReDoc: `/api/redoc`.

---

## 1. Base path

Every endpoint is mounted under **`/api`**. Nothing else is served (the docs/OpenAPI
conveniences live under `/api` too).

Clients MUST use relative URLs (`/api/...`, `/ws/...`) and never hardcode hosts such as
`localhost` or `127.0.0.1`.

## 2. Success object template

Success responses have **no envelope** — the resource is returned directly:

- **Single object** → the object itself, e.g. `GET /api/health` → `{"status": "ok", ...}`.
- **Collections** → the pagination object from §7:
  `{"items": [...], "page": 1, "page_size": 20, "total": 57, "total_pages": 3}`.
- **Status checks** → `{"status": "ok", ...}`.
- **Operations without a payload** → `{"status": "ok"}` unless the route documents otherwise.

Status codes: `200` by default, `201` for creation, `204` only when a response body is impossible.

## 3. Error object template

**All** error responses (4xx and 5xx) use exactly one template:

```json
{
  "error": {
    "code": "not_found",
    "message": "Resource not found.",
    "details": null
  }
}
```

| Field | Meaning |
|---|---|
| `error.code` | Stable snake_case machine code. Clients must branch on `code`, never parse `message`, and treat unknown codes generically. |
| `error.message` | Human-readable English text; AR/FA/EN translations are a frontend concern. |
| `error.details` | `null`, an object, or an array of objects. Validation errors (§5) use an array of `{loc, msg, type}`. |

Standard codes:

| HTTP | `code` |
|---|---|
| 400 | `bad_request` |
| 401 | `unauthorized` |
| 403 | `forbidden` |
| 404 | `not_found` |
| 405 | `method_not_allowed` |
| 409 | `conflict` |
| 422 | `validation_error` |
| 429 | `rate_limited` |
| 500 | `internal_error` |
| 503 | `service_unavailable`, `database_unreachable` |

`500` responses never leak internals (no stack traces, no exception messages in `details`).

## 4. Routes

| Method | Path | Auth | Description | Success | Errors |
|---|---|---|---|---|---|
| GET | `/api/health` | public | Process liveness and identity | 200 `HealthResponse` | — |
| GET | `/api/health/db` | public | Database connectivity check | 200 `HealthDBResponse` | 503 `database_unreachable` |

### 4.1 `GET /api/health` — liveness (public)

**Intentionally public (no authentication) — documented decision.** Reference: task
`AATM-49a40f0c-45e4-46b4-bb03-848170020d23` sets the acceptance criteria "`GET /api/health`
returns 200" and "`GET /api/health/db` returns 200", i.e. both must answer 200 without any
credentials; and the repository security rule (AGENTS.md, Q5) defines the exception clause
"every new API route requires authentication through the project's existing auth dependency,
**unless the task says the route is public**" — this task's 200-without-credentials criteria
is that declaration. Orchestrators, load balancers and CI reach them without credentials.
This decision is part of the contract and applies to both health routes; it is restated in §8.

Request: no parameters.

```bash
curl -sS http://<host>/api/health
```

Response `200`:

```json
{
  "status": "ok",
  "app": "AATM API",
  "version": "0.1.0",
  "environment": "development"
}
```

- `status` — always `"ok"`.
- `app` / `version` — process identity from `APP_NAME` / `APP_VERSION`.
- `environment` — derived from `DEBUG`: `development` when true, otherwise `production`.

### 4.2 `GET /api/health/db` — database connectivity (public)

```bash
curl -sS http://<host>/api/health/db
```

Response `200`:

```json
{
  "status": "ok",
  "database": "nexus.db",
  "dialect": "sqlite"
}
```

- `dialect` — the `DATABASE_URL` scheme (`sqlite`, `postgresql`, `mysql`, ...).
- `database` — the database name; **credentials are never returned**.
- Connectivity probe: sqlite URLs are opened directly (the default SQLite file is created
  lazily on first check); network dialects are probed with a TCP connect (2s timeout);
  unknown dialects without a host are reported without a probe.

Error `503` (unified template):

```json
{
  "error": {
    "code": "database_unreachable",
    "message": "Database is unreachable.",
    "details": {
      "dialect": "postgresql",
      "database": "aatm",
      "error_type": "OSError"
    }
  }
}
```

### 4.3 Error examples

Unknown path → `404`:

```json
{
  "error": {
    "code": "not_found",
    "message": "Resource not found.",
    "details": null
  }
}
```

Invalid query parameter (e.g. `GET /api/<route>?page=abc`) → `422`:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed.",
    "details": [
      { "loc": ["query", "page"], "msg": "Input should be a valid integer, unable to parse string as an integer", "type": "int_parsing" }
    ]
  }
}
```

## 5. Validation rules (Pydantic v2)

- Every request body and query parameter is validated by Pydantic v2 models. Violations
  return `422 validation_error` with `details` as an array of `{loc, msg, type}` items;
  `loc` is the JSON path of the offending field (e.g. `["query", "page"]`, `["body", "name"]`).
- Unknown/extra fields in request bodies are **ignored** (not rejected).
- Numbers must be JSON numbers, booleans must be `true`/`false`; string forms are rejected.
- Enum/format violations return `422`. Per-field constraints (length, ranges, trimming)
  are documented on each route.
- Identifiers and scalar fields are strings unless a route documents otherwise.
- Responses are re-validated against Pydantic response models; a server-side mismatch is a
  bug and returns `500 internal_error`.

## 6. Timestamp convention (UTC ISO-8601)

- All timestamps are **UTC**, ISO-8601, with the `Z` suffix:
  `2026-11-26T12:34:56Z` (milliseconds allowed: `2026-11-26T12:34:56.789Z`).
  Offsets like `+02:00` are never used.
- Field names end with `_at`: `created_at`, `updated_at`, `started_at`, `finished_at`, ...
- Clients render timestamps in the viewer's local timezone; the server never sends
  local time.

## 7. Pagination rules

- Query parameters: `page` (integer ≥ 1, default `1`) and `page_size` (integer 1–100,
  default `20`). Violations → `422 validation_error`.
- Response template:

  ```json
  {
    "items": [],
    "page": 1,
    "page_size": 20,
    "total": 57,
    "total_pages": 3
  }
  ```

- `total_pages = ceil(total / page_size)`; `0` when the collection is empty.
- A `page` beyond `total_pages` returns `200` with `items: []` — never `404`.
- Stable ordering per route is documented on the route; clients must not rely on
  undocumented order.

## 8. Authentication

Currently **all routes are public** — there is no auth dependency in the codebase yet.
`GET /api/health` and `GET /api/health/db` are **intentionally public without
authentication**: task `AATM-49a40f0c-45e4-46b4-bb03-848170020d23` mandates a 200 response
from both (its acceptance criteria), and AGENTS.md Q5 permits public routes "unless the
task says the route is public". They will stay public in all future phases (liveness
probes for orchestrators, load balancers and CI).

When authentication is introduced, its scheme will be defined in this section and every
protected route will be marked in §4. Protected routes will return `401 unauthorized`
(missing credentials) or `403 forbidden` (insufficient permissions) using the unified
template, and each will get a test that calls it without credentials.

## 9. Environment configuration

Server-side behaviour is configured through environment variables (see `.env.example` at
the repository root): `DATABASE_URL`, `FRONTEND_ORIGIN` (comma-separated CORS allow-list),
`LOG_LEVEL`, `APP_NAME`, `APP_VERSION`, `DEBUG`, and the optional `SECRET_KEY`. Booting the
backend requires **no API keys** and **no mandatory network connections**.

## 10. Change management

This is the project's **only** API contract file. The backend lead updates it in the same
PR as the implementation; the frontend must consume exactly what is documented here and
nothing else.
