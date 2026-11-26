# عقد واجهة برمجة التطبيقات — NEXUS OSINT API Contract

**الحالة:** عقد ثابت (ثُبّت في المهمة رقم 1). تلتزم الواجهة الأمامية بهذا العقد حرفياً:
نفس المسارات، نفس أسماء الحقول، ونفس قالب الخطأ الموحد. أي تغيير في هذا العقد يتطلب
تحديث `frontend/src/lib/api.ts` في المهمة نفسها.

**قاعدة URL:** تُقرأ من `frontend/.env.example` عبر المتغير `VITE_API_BASE_URL`.
عندما يكون فارغاً (الافتراضي) تُستخدم مسارات نسبية `/api/...` — لا تُكتب أي
مضيفات `localhost`/`127.0.0.1` داخل `frontend/src/`. يُضبط وكيل Vite في
`frontend/vite.config.ts` لتوجيه `/api` إلى الخلفية أثناء التطوير.

**المصادقة:** كل مسارات `/api/*` ما عدا `/api/health` و`/api/health/db` تتطلب
مصادقة عبر اعتماد المصادقة الموجود في المشروع (Bearer token). تُعيد الخلفية
`401`/`403` بقالب الخطأ الموحد عند غياب الاعتماد أو رفضه. الواجهة تعرض هذا
الخطأ كما هو ولا تعرض بيانات وهمية بدله.

---

## قالب الخطأ الموحد (Unified Error Template)

كل استجابة خطأ من الخلفية تحمل هذا القالب بالضبط، مع رمز الحالة HTTP المناسب:

```json
{
  "error": {
    "code": "string",
    "message": "string",
    "details": "string | null"
  }
}
```

| الحقل | النوع | الوصف |
|---|---|---|
| `error.code` | `string` | رمز آلي ثابت للخطأ (مثال: `NOT_FOUND`, `VALIDATION_ERROR`, `UNAUTHORIZED`, `BACKEND_UNAVAILABLE`) |
| `error.message` | `string` | رسالة مقروءة للمستخدم |
| `error.details` | `string \| null` | تفاصيل إضافية اختيارية (أو `null`) |

عميل الواجهة `frontend/src/lib/api.ts` يحوّل أي استجابة خطأ إلى `ApiError`
يحمل `status` و`code` و`message` و`details`، ويرميه للمستدعي. عند تعذّر الاتصال
بالشبكة (الخلفية غير مشغّلة) يرمي `ApiError` برمز `NETWORK_ERROR` وحالة `0`.

---

## نقاط النهاية (Endpoints)

### 1. فحص الصحة — `GET /api/health` (عام، بلا مصادقة)

```json
{
  "status": "ok | degraded | error",
  "version": "string",
  "timestamp": "string (ISO-8601 UTC)"
}
```

### 2. صحة قاعدة البيانات — `GET /api/health/db` (عام، بلا مصادقة)

```json
{
  "status": "ok | degraded | error",
  "database": "string",
  "latency_ms": "number"
}
```

### 3. التحقيقات الأخيرة — `GET /api/investigations/recent?limit=5`

```json
{
  "items": [
    {
      "id": "string",
      "query": "string",
      "query_type": "name | username | email | phone | url | domain | entity",
      "status": "queued | running | completed | failed",
      "created_at": "string (ISO-8601 UTC)"
    }
  ],
  "total": "number"
}
```

### 4. إحصاءات البحث — `GET /api/stats`

```json
{
  "total_investigations": "number",
  "total_searches": "number",
  "success_rate": "number (0-100)",
  "avg_duration_ms": "number"
}
```

### 5. التكاملات المتاحة — `GET /api/integrations`

```json
{
  "items": [
    {
      "id": "string",
      "name": "string",
      "status": "available | unavailable | disabled",
      "description": "string"
    }
  ]
}
```

### 6. حالة مزود الذكاء الاصطناعي — `GET /api/ai/provider`

```json
{
  "provider": "string",
  "model": "string",
  "status": "available | unavailable | not_configured",
  "latency_ms": "number | null"
}
```

### 7. تقدم المهام — `GET /api/tasks/progress`

```json
{
  "items": [
    {
      "id": "string",
      "name": "string",
      "status": "queued | running | completed | failed",
      "progress": "number (0-100)"
    }
  ],
  "total": "number"
}
```

### 8. آخر التقارير — `GET /api/reports/latest?limit=5`

```json
{
  "items": [
    {
      "id": "string",
      "title": "string",
      "status": "ready | generating | failed",
      "created_at": "string (ISO-8601 UTC)"
    }
  ],
  "total": "number"
}
```

### 9. بدء تحقيق — `POST /api/investigations`

الطلب:

```json
{
  "query": "string",
  "query_type": "name | username | email | phone | url | domain | entity"
}
```

الاستجابة `201`:

```json
{
  "id": "string",
  "query": "string",
  "query_type": "name | username | email | phone | url | domain | entity",
  "status": "queued | running",
  "created_at": "string (ISO-8601 UTC)"
}
```

---

## ملاحظات ملزمة للواجهة

1. لا تُعرض أي بيانات وهمية كأنها نتائج بحث حقيقية. عند فشل أي طلب يُعرض
   الخطأ أو حالة فارغة واضحة.
2. الصفحات غير المنفذة في هذه المرحلة تعرض حالة فارغة (`Placeholder`) ولا
   تدّعي تنفيذاً.
3. كل أزرار/حقول/محددات تحمل `label` و`aria` وتباين ألوان كافٍ، وتُستخدم
   خصائص CSS المنطقية (`ms-`, `me-`, `ps-`, `pe-`, `text-start`, `text-end`)
   للحفاظ على التكافؤ بين LTR وRTL.
