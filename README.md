# test-program — لعبة تطابق البطاقات + خلفية النقاط ولوحة الصدارة

المستودع يحتوي جزأين متكاملين:

1. **الواجهة (Frontend):** لعبة خفيفة تُلعَب في المتصفح مبنية باستخدام **React + TypeScript + Vite + Tailwind CSS** مع دعم كامل للغة العربية واتجاه **RTL** (`dir="rtl"`).
2. **الخلفية (Backend):** خدمة **FastAPI + SQLAlchemy** تُغذّي الواجهة بنقطتين فقط: استقبال نتيجة جولة منتهية، ولوحة صدارة مرتبة بأقل المحاولات ثم أقل مدة. لا مصادقة ولا مستخدمين — المهمة للعبة خفيفة.

---

# الواجهة: لعبة تطابق البطاقات (Memory Card Matching Game)

## المميزات
- ثلاث مستويات صعوبة: **سهل (4×3)**، **عادي (4×4)**، **صعب (6×4)**.
- عدّاد محاولات ومؤقّت يبدأ مع أول نقرة.
- شاشة نهاية تعرض النتيجة مع إمكانية إرسالها إلى نقطة API خارجية (`VITE_SCORE_API_URL` أو `/api/scores`) مع معالجة فشل الشبكة بلطف.
- بنية نصوص قابلة للتوسعة للغات أخرى لاحقًا (`src/i18n/strings.ts`).

## التشغيل محليًا
```bash
npm install
npm run dev
```

## البناء للإنتاج
```bash
npm run build
```

## تشغيل الاختبارات
```bash
npm test
```

### ربط الواجهة بالخلفية

الواجهة ترسل النتيجة عبر `POST` إلى `VITE_SCORE_API_URL` (أو `/api/scores` افتراضيًا). لتوصيلها بالخلفية المحلية:

```bash
VITE_SCORE_API_URL="http://localhost:8000/api/v1/scores" npm run dev
```

ملاحظة: لا يوجد حاليًا proxy في `vite.config.ts` لمسار `/api/scores` الافتراضي؛ استخدم `VITE_SCORE_API_URL` كما أعلاه حتى تعمل الإرسالات مباشرة.

---

# الخلفية: خدمة نقاط اللعبة ولوحة الصدارة

خدمة FastAPI صغيرة تُغذّي واجهة اللعبة بنقطتين فقط: استقبال نتيجة جولة منتهية، ولوحة صدارة مرتبة بأقل المحاولات ثم أقل مدة. لا مصادقة ولا مستخدمين — المهمة مخصّصة للعبة خفيفة.

## نقاط النهاية (Endpoints)

| Method | Path | الوصف |
|--------|------|-------|
| `GET` | `/health` | فحص صحة الخدمة، يعيد `{"status": "ok"}` |
| `POST` | `/api/v1/scores` | استقبال نتيجة (يعيد `201` مع مُعرّف النتيجة) |
| `GET` | `/api/v1/leaderboard` | أفضل النتائج مرتبة بأقل محاولات ثم أقل مدة |

### POST /api/v1/scores

الحمولة (JSON) مع تحقق صارم عبر Pydantic:

```json
{
  "player_name": "sara",
  "difficulty": "easy",
  "attempts": 4,
  "duration_seconds": 25.5,
  "finished_at": "2026-11-21T10:00:00Z"
}
```

- `player_name`: نص من 1 إلى 40 حرفًا (يُزال الفراغ الزائد تلقائيًا)
- `difficulty`: واحدة من `easy` / `medium` / `hard`
- `attempts`: عدد صحيح أكبر من 0 (وبحد أقصى معقول 10000)
- `duration_seconds`: رقم أكبر من 0 وبحد أقصى 86400 (يوم واحد)
- `finished_at`: تاريخ/وقت ISO-8601، اختياري — يُستخدم الوقت الحالي عند الإغفال

أي مخالفة تعيد `422` مع تفاصيل الخطأ.

### GET /api/v1/leaderboard

- `difficulty` (اختياري): حصر النتائج على صعوبة واحدة، وغير الصالحة تعيد `422`
- `limit` (اختياري): عدد الصفوف، افتراضيًا `10` ويجب أن يكون بين 1 و 50
- الترتيب: أقل محاولات أولًا، ثم أقل مدة، مع حقل `rank` يبدأ من 1

## التشغيل

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# إلزامي قبل أول إقلاع: إنشاء قاعدة البيانات من الصفر عبر الترحيلات
alembic upgrade head

uvicorn app.main:app --host 0.0.0.0 --port 8000
```

> الخطوة `alembic upgrade head` **إلزامية** وليست اختيارية: الخدمة لا تُنشئ الجداول بنفسها عند الإقلاع (لا يوجد `create_all`)، وعند أول تشغيل بقاعدة فارغة بدون ترحيل سيفشل كل استدعاء لـ `/api/v1/scores` أو `/api/v1/leaderboard` بخطأ `no such table: scores`.

ثم افتح:

- الواجهة التفاعلية: <http://localhost:8000/docs>
- فحص الصحة: <http://localhost:8000/health>

## الاختبارات

```bash
pip install -r requirements-dev.txt
pytest
```

تشمل الاختبارات: إدخال صالح، رفض الإدخال غير الصالح (422)، ترتيب لوحة الصدارة، فلتر الصعوبة، حد `limit`، ترويسات CORS وتحليل `CORS_ORIGINS` من البيئة، التطبيع إلى UTC للتواريخ، والتأكد من أن الترحيلات تُنشئ الجداول من الصفر.

فحص التنسيق (lint):

```bash
ruff check app tests alembic
```

## ترحيل قاعدة البيانات (Migrations)

الترحيلات موجودة في `alembic/versions/` وتُدار عبر Alembic:

```bash
# ترقية من الصفر إلى آخر نسخة
alembic upgrade head

# الترجمة للخلف خطوة واحدة
alembic downgrade -1

# إنشاء ترحيل جديد بعد تعديل النماذج
alembic revision --autogenerate -m "وصف التغيير"
```

يعمل `alembic upgrade head` من الصفر (قاعدة بيانات فارغة) وينشئ جدول `scores` مع فهارسه.

## قاعدة البيانات

التخزين عبر SQLAlchemy. الافتراضي SQLite، ويمكن التحويل إلى PostgreSQL بمتغير بيئة واحد:

```bash
# SQLite (افتراضي)
DATABASE_URL=sqlite:///./scores.db

# PostgreSQL
DATABASE_URL=postgresql://user:password@localhost:5432/scores
alembic upgrade head
```

## متغيرات البيئة (الخلفية)

| المتغير | الافتراضي | الوصف |
|---------|-----------|-------|
| `DATABASE_URL` | `sqlite:///./scores.db` | رابط قاعدة البيانات (SQLite أو PostgreSQL) |
| `CORS_ORIGINS` | `http://localhost:5173` | قائمة الأصول المسموح بها مفصولة بفواصل |
| `VITE_SCORE_API_URL` (الواجهة) | `/api/scores` | رابط نقطة استقبال النتائج التي ترسل إليها الواجهة |

CORS محصور افتراضيًا على `http://localhost:5173` (خادم Vite dev) عبر الإعداد فقط — لا يوجد أصل مكتوب ثابتًا في الكود. لتغييره:

```bash
CORS_ORIGINS="http://localhost:5173,http://localhost:3000" uvicorn app.main:app --port 8000
```

**صيغة `CORS_ORIGINS` المدعومة:** قائمة مفصولة بفواصل (الصيغة الأساسية)، أو نص JSON مصفوفة مثل `'["http://localhost:5173","http://localhost:3000"]'`. الفواصل الزائدة والفراغات حول الأصل تُتجاهل تلقائيًا.

يمكن نسخ `.env.example` إلى `.env` لضبط المتغيرات محليًا (لا تُرفع `.env` إلى المستودع) — السيناريو مُختبَر حرفيًا: `cp .env.example .env` ثم `uvicorn app.main:app` يعمل مباشرة.

## التواريخ والمنطقة الزمنية (ملاحظة لعملاء الواجهة)

- SQLite يخزّن التواريخ **بدون منطقة زمنية** ويعيدها naive؛ لذلك تُطبَّع جميع التواريخ في الطلبات والاستجابات إلى **UTC**: أي `finished_at` يُرسل بلا منطقة زمنية يُفترض أنه UTC، وأي `finished_at` بمنطقة زمنية (مثل `2026-11-21T12:00:00+02:00`) يُحوَّل إلى UTC قبل التخزين.
- جميع الاستجابات تعيد التواريخ بلحظة UTC صريحة بصيغة ISO-8601 مع `Z` (مثل `"finished_at": "2026-11-21T10:00:00Z"`)، ولمرة `created_at` نفس الشيء.
- **يُفضّل دائمًا** أن يرسل الواجهة `finished_at` بصيغة `Z` أو مع إزاحة صريحة؛ مع PostgreSQL (`timestamptz`) يُحفظ التوقيت بكامل دقته، ومع SQLite تُحفظ لحظة UTC نفسها بعد التطبيع.

## بنية المشروع

```
app/                  # الخلفية
  main.py             # إنشاء التطبيق، CORS، /health
  config.py           # الإعدادات من متغيرات البيئة (pydantic-settings)
  database.py         # محرّك SQLAlchemy والجلسات
  models.py           # نموذج Score
  schemas.py          # مخططات Pydantic والتحقق وتطبيع UTC
  routers/
    scores.py         # POST /api/v1/scores و GET /api/v1/leaderboard
alembic/
  env.py              # بيئة الترحيل (تقرأ DATABASE_URL من الإعدادات)
  versions/           # الترحيلات (0001: إنشاء جدول scores)
tests/                # اختبارات pytest للخلفية
src/                  # الواجهة (React + TypeScript + Vite)
index.html
vite.config.ts
```
