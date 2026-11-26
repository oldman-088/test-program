# لعبة تطابق البطاقات — Memory Matching Game

لعبة ذاكرة عربية (RTL) كاملة: واجهة **React + TypeScript + Vite** وخلفية **FastAPI + SQLAlchemy + Alembic**
لحفظ النتائج ولوحة الصدارة.

A complete Arabic (RTL) memory card-matching game with a FastAPI leaderboard service.

```
frontend/   React 18 + TypeScript + Vite (RTL, Arabic UI)
backend/    FastAPI + SQLAlchemy 2 + Alembic + SQLite/PostgreSQL
```

---

## 1. المميزات / Features

**الواجهة (Frontend)**

- ثلاثة مستويات صعوبة: سهل (٦ أزواج)، متوسط (٨ أزواج)، صعب (١٢ زوجًا) — شبكات 4/4/6 أعمدة.
- مؤقّت يبدأ من أول بطاقة مقلوبة، عدّاد محاولات وحركات وأفضل تتابع، ونسبة دقّة.
- قلب البطاقات ثلاثي الأبعاد، تمييز الأزواج المتطابقة، وتأخير أنيق للبطاقات غير المتطابقة.
- شاشة نهاية تعرض الملخّص وتسمح بحفظ النتيجة باسم اللاعب (تحقّق من 1–40 حرفًا).
- لوحة صدارة مباشرة لكل مستوى، مع تمييز صفّك بعد الحفظ وإعادة تحميل تلقائية.
- تصميم عربي بالكامل: `dir="rtl"`, خط Cairo, أرقام عربية-هندية في العرض، وواجهة متجاوبة.
- إتاحة (a11y): أدوار `grid`/`dialog`/`radiogroup`، تسميات `aria-label`، واحترام `prefers-reduced-motion`.

**الخلفية (Backend)**

- `POST /api/v1/scores` — حفظ نتيجة (اسم اللاعب، المستوى، المحاولات، المدة، وقت الانتهاء).
- `GET /api/v1/leaderboard?difficulty=&limit=` — أفضل النتائج مرتبة بالمحاولات ثم الوقت ثم وقت الانتهاء.
- `GET /api/v1/stats` — إحصاءات مختصرة لكل مستوى.
- `GET /health` — فحص صحة الخدمة.
- تحقّق صارم من المدخلات عبر Pydantic (أسماء فارغة/طويلة، محاولات ≤ 0، مدة خارج الحدود، مستوى غير معروف…).
- CORS قابل للضبط، SQLite افتراضيًا ودعم PostgreSQL، وهجرة Alembic واحدة.

---

## 2. التشغيل السريع / Quick start

### الخلفية / API

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env          # اختياري — القيم الافتراضية تعمل مباشرة
alembic upgrade head          # إنشاء قاعدة البيانات
uvicorn app.main:app --reload --port 8000
```

- الواجهة التفاعلية للمستندات: <http://localhost:8000/docs>
- الفحص: `curl http://localhost:8000/health` → `{"status":"ok","version":"1.0.0"}`

### الواجهة / Frontend

```bash
cd frontend
npm install
npm run dev                   # http://localhost:5173
```

يعمل خادم التطوير كوسيط (proxy) تلقائيًا لـ `/api` و `/health` نحو `http://127.0.0.1:8000`
حتى لا يتحدث المتصفح مع أكثر من أصل واحد (no CORS needed). لتغيير العنوان:

```bash
VITE_API_PROXY_TARGET=http://127.0.0.1:9000 npm run dev
```

### تشغيل على منفذ واحد (إنتاج)

يمكن لـ FastAPI تقديم الحزمة المبنية بنفسه:

```bash
cd frontend && npm run build
cd ../backend && FRONTEND_DIST=../frontend/dist uvicorn app.main:app --port 8000
# اللعبة على http://localhost:8000 والـ API تحت /api/v1
```

---

## 3. الإعدادات / Configuration

كل القيم عبر متغيّرات بيئة أو ملف `backend/.env` (انظر `backend/.env.example`):

| المتغيّر | الافتراضي | الوصف |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./scores.db` | اتصال SQLAlchemy (PostgreSQL مدعوم) |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | أصول مفصولة بفواصل |
| `AUTO_CREATE_SCHEMA` | `true` | إنشاء الجداول عند الإقلاع للتطوير |
| `FRONTEND_DIST` | — | مسار حزمة الواجهة المبنية لتقديمها من نفس الخادم |

---

## 4. الـ API

```http
POST /api/v1/scores
Content-Type: application/json

{
  "player_name": "ليلى",
  "difficulty": "easy",
  "attempts": 8,
  "duration_seconds": 51,
  "finished_at": "2026-11-26T10:00:00Z"   // اختياري
}
```

`201 Created`

```json
{
  "id": 1,
  "player_name": "ليلى",
  "difficulty": "easy",
  "attempts": 8,
  "duration_seconds": 51,
  "finished_at": "2026-11-26T05:22:25.898300Z"
}
```

```http
GET /api/v1/leaderboard?difficulty=easy&limit=10
```

```json
{
  "difficulty": "easy",
  "limit": 10,
  "total": 1,
  "entries": [
    {
      "id": 1,
      "rank": 1,
      "player_name": "ليلى",
      "difficulty": "easy",
      "attempts": 8,
      "duration_seconds": 51,
      "finished_at": "2026-11-26T05:22:25.898300Z"
    }
  ]
}
```

الترتيب: **أقل محاولات → أقل مدة → أقدم وقت انتهاء → المعرّف** (ترتيب حتمي ومستقر).
الحدود: `player_name` 1–40 حرفًا بعد إزالة الفراغات، `attempts` 1–10000،
`duration_seconds` 1–86400، `limit` 1–50. أي انتهاك → `422`.

---

## 5. الاختبارات / Tests

```bash
# الخلفية — 37 اختبارًا (pytest)
cd backend && .venv/bin/pytest -q
cd backend && .venv/bin/ruff check app tests alembic

# الواجهة — 40 اختبارًا (vitest) + فحص الأنواع + بناء إنتاجي
cd frontend && npm test
cd frontend && npx tsc --noEmit
cd frontend && npm run build
```

تغطية الخلفية: إنشاء/رفض النتائج، إزالة الفراغات، المناطق الزمنية، ترتيب لوحة الصدارة
وحدودها، إحصاءات، CORS (قبول/رفض preflight)، والهجرات (ترقية → تراجع → ترقية على قاعدة جديدة).
تغطية الواجهة: منطق اللعب النقي (خلط، إقلاع، مطابقة/خطأ، فوز، أدوات تنسيق)، آلة حالة اللعبة
(المؤقّت، تأخير إخفاء الخطأ، الفوز، تغيير المستوى)، عميل الـ API، شاشة النهاية (تحقّق/حفظ/فشل)،
والتطبيق الكامل (RTL، تبديل الصعوبة، قلب البطاقات، لوحة الصدارة، حالة الخطأ).

---

## 6. البنية / Project layout

```
backend/
  app/main.py            مصنع تطبيق FastAPI + تقديم SPA اختياري
  app/config.py          إعدادات pydantic-settings
  app/database.py        المحرّك والجلسات
  app/models.py          نموذج Score + نوع UTC
  app/schemas.py         مخططات الطلب/الاستجابة
  app/routers/scores.py  نقاط النهاية
  alembic/versions/      هجرة 0001 (جدول scores + فهارس)
  tests/                 pytest (37)

frontend/
  src/game/              أنواع + منطق نقي (deck, flip, wins) + اختبارات
  src/hooks/useGame.ts   آلة حالة اللعبة والمؤقّت
  src/components/        Board, Card, DifficultyPicker, Scoreboard, Leaderboard, EndScreen
  src/services/scoreApi.ts
```

## 7. ملاحظات / Notes

- لا مصادقة ولا مستخدمين — لعبة خفيفة، الاسم يُكتب في شاشة النهاية فقط.
- لا أسرار أو ملفات بيئة أو قواعد بيانات داخل المستودع (`*.db`, `.env` مستثناة).
