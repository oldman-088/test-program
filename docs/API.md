# عقد واجهة الخلفية — `docs/API.md`

**المهمة:** AATM-984687b7 · البند 21 (بنية اختبارات الخلفية + اختبار تطابق العقد)
**المرجع التنفيذي:** `backend/tests/test_contract.py` — هذا الملف ليس شرحاً حرّاً، بل **عقد يُقارَن
آلياً** بمسارات `backend/app/api/`. أي انحراف في الاتجاهين (مسار موثّق بلا تنفيذ، أو تنفيذ موثّق
بخلاف الوثيقة، أو تغيّر قالب الخطأ) يُحمّر الاختبار.

| العنصر | القيمة |
|---|---|
| البادئة العقدية لكل المسارات | `/api/v1` |
| مصادقة نقاط العمل | ترويسة `X-API-Key` (المفتاح من `API_KEY`) |
| تتبّع الطلب | `X-Request-ID` تُصدَّع في كل استجابة |
| ترميز أجسام الأخطاء | `application/json` (UTF-8 بحكم RFC 8259) |

---

## 1. جدول المسارات العقدية

المتن في العمود `Example` هو استعلام إلزامي يُلحق بالمسار عند التنفيذ الآلي للاختبار،
حتى تُقاس «حالة النجاح» على طلب مكتمل الشروط لا على طلب ناقص.

| Method | Path | Auth | Success | Example |
|---|---|---|---|---|
| `GET` | `/api/v1/health` | `no` | `200` | `-` |
| `GET` | `/api/v1/health/ready` | `no` | `200` | `-` |
| `POST` | `/api/v1/sessions` | `yes` | `201` | `-` |
| `GET` | `/api/v1/sessions` | `yes` | `200` | `?employee_id=worker-7` |
| `GET` | `/api/v1/sessions/{session_id}` | `yes` | `200` | `-` |
| `DELETE` | `/api/v1/sessions/{session_id}` | `yes` | `204` | `-` |

**قواعد المطابقة الآلية**

1. مجموعة أزواج `(Method, Path)` أعلاه = مجموعة مسارات `app.routes` التي تبدأ بـ `/api/v1` حرفياً.
2. `Auth: yes` ⇒ استدعاء بلا ترويسة `X-API-Key` يجب أن يُرجع `401`. و`Auth: no` ⇒ لا `401` ولا `403`.
3. `Success` ⇒ استدعاء مع مصادقة صحيحة ومثال مكتمل يُرجع الحالة نفسها.
4. أي مسار يُضاف إلى `backend/app/api/routes/` دون صفّ هنا ⇒ فشل العقد.

---

## 2. قالب الخطأ الموحد

**كل** استجابة خطأ — أخطاء التطبيق، وأخطاء تحقّق Pydantic، و`404` المسارات غير المعروفة،
والأخطاء غير المعالجة `500` — تحمل البنية نفسها، بمفاتيح لا تُزاد ولا تُنقص:

```json
{
  "error": {
    "code": "not_found",
    "message": "الجلسة ses_00000000000000000000 غير موجودة.",
    "details": [],
    "request_id": "6f1d2c4a8b9e4f70a1b2c3d4e5f60718"
  }
}
```

| المفتاح | النوع | الوصف |
|---|---|---|
| `error` | object | المفتاح الجذري الوحيد. لا `detail` ولا `message` عُرياً. |
| `error.code` | string | رمز ثابت من الجدول في §3. |
| `error.message` | string | رسالة آمنة قابلة للعرض؛ لا تسرّب نص استثناء داخلي. |
| `error.details` | array | قائمة (قد تكون فارغة) بتفاصيل التحقّق. الاستثناء الموثّق الوحيد: كائن تفاصيل مُهيّأ في `503` من `GET /api/health/db` (انظر §6.4). |
| `error.request_id` | string \| null | معرّف الطلب، أو `null` عند المستويات الدنيا. |

### 2.1 مثال خطأ التحقق (Pydantic)

`details` لا يكون كائناً عشوائياً: مفاتيحه العقدية الأربعة أدناه مطابقة حرفياً.

```json
{
  "error": {
    "code": "validation_error",
    "message": "تحقق واحد على الأقل فشل (2).",
    "details": [
      {
        "field": "body.task_id",
        "loc": ["body", "task_id"],
        "message": "String should have at least 8 characters",
        "type": "string_too_short"
      }
    ],
    "request_id": "6f1d2c4a8b9e4f70a1b2c3d4e5f60718"
  }
}
```

---

## 3. أكواد الخطأ المعتمدة

المجموعة أدناه = `app.core.errors.ERROR_REGISTRY ∪ HTTP_STATUS_TO_CODE` مطابقةً ثنائية الاتجاه.

| Code | HTTP | متى |
|---|---|---|
| `bad_request` | `400` | طلب غير مفهوم من Starlette. |
| `unauthenticated` | `401` | لا `X-API-Key` أو المفتاح خاطئ. |
| `permission_denied` | `403` | مفتاح صالح بلا صلاحية على المورد. |
| `not_found` | `404` | معرّف غير موجود، أو مسار غير موثّق. |
| `method_not_allowed` | `405` | طريقة غير معرّفة على مسار موجود. |
| `conflict` | `409` | تعارض مع حالة قائمة (تكرار `task_id`). |
| `payload_too_large` | `413` | جسم فوق الحد. |
| `validation_error` | `422` | تحقّق Pydantic (جسم/استعلام/مسار). |
| `rate_limited` | `429` | تجاوز حد الطلبات. |
| `api_error` | `500` | والد كل أخطاء التطبيق عند لا كود أدق. |
| `configuration_error` | `500` | ضبط ناقص على الخادم (مثل `API_KEY` فارغ). |
| `internal_error` | `500` | استثناء غير معالج — نصّه يُسجَّل ولا يُرسل. |
| `upstream_unavailable` | `502` | فشل خدمة خارجية (مزوَّرة في الاختبارات). |
| `database_unavailable` | `503` | فشل `SELECT 1` في `/health/ready` أو في معاملة. |
| `database_unreachable` | `503` | فشل فحص الاتصال في `GET /api/health/db` (سطح `/api`، §6). |

---

## 4. حالات الجلسة (`status`)

مجموعة القيم في `app.models.session.SESSION_STATUSES` — تُقارن آلياً بهذه القائمة:

- `queued` — في انتظار المجدول.
- `running` — العامل منفّذ في worktree.
- `review` — مفتوح للمراجعة.
- `completed` — اكتمل واندماج.
- `failed` — فشل بعد استنفاد `attempts`.

---

## 5. خارج العقد

نقاط التوثيق نفسها خارج جدول العقد ولا تُطالَب بأن تكون موثّقة كمسار عمل:
`GET /docs` و`GET /openapi.json` (و`/redoc` معطّل)، مع مرآتَين تحت `/api`:
`GET /api/openapi.json` (نفس محتوى المخطط) و`GET /api/docs` (تحويل إلى `/docs`).

**ملاحظة شفافية:** لا يوجد في هذه المستودع أي تنفيذ لخدمات مدفوعة؛ الاختبارات ترفض صراحةً
فتح مقبس شبكي خارج `127.0.0.1`، وكل ما هو خارجي مزوَّر.

---
---

# Appendix — Public `/api` surface contract (AATM-49a40f0c)

> This appendix documents the **public `/api` surface** merged from task
> `AATM-49a40f0c-45e4-46b4-bb03-848170020d23` (health endpoints). It is part of this
> contract file; where it overlaps with sections 1–5 above, **the platform envelope of
> §2 and the code table of §3 are authoritative** (the reconciliation keeps one unified
> error template application-wide).

- Stack: FastAPI with Pydantic v2.
- OpenAPI document: `GET /api/openapi.json` (identical to `/openapi.json`) · Swagger UI:
  `/api/docs` (redirects to `/docs`) · ReDoc: disabled (see §5).

## 6.1 Base path of this surface

Every endpoint of this surface is mounted under **`/api`** (outside the `/api/v1`
contract prefix). The health routes below are **intentionally public** (no
authentication): task `AATM-49a40f0c-...` mandates `200` from both without credentials,
and the repository security rule (AGENTS.md Q5) permits public routes when the task says
so. Orchestrators, load balancers and CI reach them without credentials.

Clients MUST use relative URLs (`/api/...`) and never hardcode hosts such as
`localhost` or `127.0.0.1`.

## 6.2 Success object template

Success responses have **no envelope** — the resource is returned directly:

- **Single object** → the object itself, e.g. `GET /api/health` → `{"status": "ok", ...}`.
- **Collections** → the pagination object from §6.7.
- **Status checks** → `{"status": "ok", ...}`.
- **Operations without a payload** → `{"status": "ok"}` unless the route documents otherwise.

Status codes: `200` by default, `201` for creation, `204` only when a response body is impossible.

## 6.3 Error object template (unified platform envelope)

**All** error responses (4xx and 5xx), on this surface as well, use the §2 template:

```json
{
  "error": {
    "code": "database_unreachable",
    "message": "Database is unreachable.",
    "details": {
      "dialect": "postgresql",
      "database": "aatm",
      "error_type": "OSError"
    },
    "request_id": "6f1d2c4a8b9e4f70a1b2c3d4e5f60718"
  }
}
```

- `error.code` — stable snake_case machine code from the table in §3. Clients must branch
  on `code`, never parse `message`, and treat unknown codes generically.
- `error.message` — human-readable text. `500` responses never leak internals.
- `error.details` — an array of `{field, loc, message, type}` items for validation errors
  (§2.1), `[]` when there is nothing to report, or — one documented structured case — an
  object carrying diagnostics for `database_unreachable` from `GET /api/health/db`
  (§6.4). The object never contains credentials.

## 6.4 Routes of this surface

| Verb | Endpoint | Auth | Description | Success | Errors |
|---|---|---|---|---|---|
| GET | `/api/health` | public | Process liveness and identity | 200 `HealthResponse` | — |
| GET | `/api/health/db` | public | Database connectivity check | 200 `HealthDBResponse` | 503 `database_unreachable` |

### `GET /api/health` — liveness (public)

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
- `environment` — the configured `ENVIRONMENT`: `development`, `test`, `staging` or
  `production` (reconciled with the platform settings; `development` is the default).

### `GET /api/health/db` — database connectivity (public)

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

Error `503` (unified template with the structured `details` object of §6.3):

```json
{
  "error": {
    "code": "database_unreachable",
    "message": "Database is unreachable.",
    "details": {
      "dialect": "postgresql",
      "database": "aatm",
      "error_type": "OSError"
    },
    "request_id": "6f1d2c4a8b9e4f70a1b2c3d4e5f60718"
  }
}
```

### Error examples (this surface)

Unknown path → `404`:

```json
{
  "error": {
    "code": "not_found",
    "message": "المطلوب غير موجود.",
    "details": [],
    "request_id": "6f1d2c4a8b9e4f70a1b2c3d4e5f60718"
  }
}
```

Invalid query parameter → `422`:

```json
{
  "error": {
    "code": "validation_error",
    "message": "تحقق واحد على الأقل فشل (1).",
    "details": [
      {
        "field": "page",
        "loc": ["query", "page"],
        "message": "Input should be a valid integer, unable to parse string as an integer",
        "type": "int_parsing"
      }
    ],
    "request_id": "6f1d2c4a8b9e4f70a1b2c3d4e5f60718"
  }
}
```

## 6.5 Validation rules (Pydantic v2)

- Every request body and query parameter is validated by Pydantic v2 models. Violations
  return `422 validation_error` with `details` as an array of `{field, loc, message, type}`
  items (§2.1); `loc` is the JSON path of the offending field.
- Unknown/extra fields in request bodies are **rejected** (`extra_forbidden`), matching the
  platform schemas (reconciled with `backend/app/schemas/`).
- Numbers must be JSON numbers, booleans must be `true`/`false`; string forms are rejected.
- Enum/format violations return `422`. Per-field constraints are documented on each route.
- Responses are re-validated against Pydantic response models; a server-side mismatch is a
  bug and returns `500 internal_error`.

## 6.6 Timestamp convention (UTC ISO-8601)

- All timestamps are **UTC**, ISO-8601, with the `Z` suffix:
  `2026-11-26T12:34:56Z` (milliseconds allowed: `2026-11-26T12:34:56.789Z`).
  Offsets like `+02:00` are never used.
- Field names end with `_at`: `created_at`, `updated_at`, `started_at`, `finished_at`, ...
- Clients render timestamps in the viewer's local timezone; the server never sends local time.

## 6.7 Pagination rules (collection convention)

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
- Stable ordering per route is documented on the route.
- Reconciled note: current `/api/v1` collections document their own query parameters (for
  example `limit` on `GET /api/v1/sessions`); the template above is the platform
  convention for collection routes on either surface.

## 6.8 Authentication

`GET /api/health` and `GET /api/health/db` are **intentionally public** (see §6.1) and
stay public in all future phases. The `/api/v1` surface is protected by the `X-API-Key`
header per §1. When authentication is extended to new routes, each protected route is
marked in its table and returns `401 unauthenticated` / `403 permission_denied` using the
unified template.

## 6.9 Environment configuration

Server-side behaviour is configured through environment variables (see `.env.example` at
the repository root): `APP_NAME`, `ENVIRONMENT`, `DEBUG`, `LOG_LEVEL`, `DATABASE_URL`,
`APP_VERSION`, `API_KEY`, `SECRET_KEY` (optional), `CORS_ALLOW_ORIGINS` and
`FRONTEND_ORIGIN` (comma-separated CORS allow-lists). Booting the backend requires **no
API keys** and **no mandatory network connections** — every field has a working default
and `SECRET_KEY` may stay unset.

## 6.10 Change management

This file is the project's **only** API contract: sections 1–5 govern the `/api/v1`
contract (machine-checked by `backend/tests/test_contract.py`) and this appendix governs
the public `/api` surface. Any new or changed endpoint must be documented here **in the
same pull request** that implements it. If code and this file disagree, the code is wrong.
