# NEXUS OSINT — المرحلة 1: فحص البيئة وتأسيس هيكل المشروع

## نظرة عامة
نظام **NEXUS OSINT** هو منصة لإدارة فريق من الموظفين الاصطناعيين (AI Agent Team Manager): مدير يحول التوجيهات إلى مهام، وعمال ينفذونها في فروع Git معزولة، ومراجع يراجع الطلبات قبل الدمج. يعتمد النظام على واجهة أمامية (React، AR/FA/EN) تتصل بواجهة خلفية (FastAPI)، مع أوكستراتور وجدولة ومزودي نماذج ومتصفح سواقة ولوحة قيادة.

## ما أُنجز في هذه المرحلة فقط (المرحلة 1)
هذه المرحلة توثيقية وتأسيسية فقط. لا تُنفذ أي ميزة تطبيقية، ولا تُحجب أي مهمة أخرى، ولا تعتمد على أي مهمة.

المخرجات التي أُضيفت في هذه المرحلة:
- `README.md` (هذا الملف) — نظرة عامة على NEXUS OSINT، ما أُنجز في المرحلة 1 فقط، بنية المشروع، تعليمات تشغيل سريعة، وتنبيه بأن المراحل 2–7 لم تُنفذ بعد.
- `LICENSE` — رخصة MIT باسم صاحب المشروع (NEXUS OSINT Project Owner).
- `.gitignore` — يستثني `node_modules` و `dist` و `.venv` و `__pycache__` و `.pytest_cache` و `.env` و `*.sqlite3` و `.mypy_cache`.
- `docs/ENVIRONMENT.md` — نتائج فحص البيئة: النظام، والإصدارات، والأدوات المتاحة وغير المتاحة، والقيود.
- `docs/ROADMAP.md` — المراحل السبعة بالترتيب مع حالة كل مرحلة ومخرجاتها المتوقعة.
- `scripts/setup.sh` — نص برمجي لغرفة لينكس/ماك لإنشاء البيئة وتثبيت الاعتماديات وتوليد `.env`.
- `scripts/setup.ps1` — نص برمجي لبيئة PowerShell (ويندوز) لنفس الغرض.
- `tests/` — اختبارات آلية تؤكد وجود المخرجات وصلاحيتها.

## بنية المشروع (بند 20 من المواصفة)
```
NEXUS OSINT/
├── README.md
├── LICENSE
├── .gitignore
├── .env.example
├── docs/
│   ├── ENVIRONMENT.md
│   └── ROADMAP.md
├── scripts/
│   ├── setup.sh
│   └── setup.ps1
├── tests/
│   └── test_phase1.py
├── backend/        (لم يُنشأ بعد — المرحلة 2)
│   └── app/
│       ├── api/routes/
│       └── orchestration/
├── frontend/       (لم يُنشأ بعد — المرحلة 7)
└── ...
```

## تعليمات تشغيل سريعة

### الواجهة الخلفية (الباك إند)
```bash
# إنشاء البيئة الافتراضية وتثبيت متطلبات بايثون
chmod +x scripts/setup.sh
./scripts/setup.sh

# أو يدويًا
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt   # عند توفرها في المرحلة 2

# تشغيل الخادم (عند توفر الكود)
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### الواجهة الأمامية (فرونت إند)
```bash
cd frontend
npm install
npm run dev
# عند توفر الكود في المرحلة 7، يُشغل الخادم على http://localhost:3000
```

### التشغيل بالحاويات (docker compose)
```bash
cp .env.example .env
docker compose up -d --build      # البناء + التشغيل (يتطلب Docker)
# الواجهة: http://localhost:3000  (nginx يخدم الملفات ويوجّه /api و /ws إلى الخلفية)
# الخلفية:  http://localhost:8000/api/health
docker compose down               # إيقاف مع بقاء بيانات SQLite (volume: nexus-osint-data)
docker compose down -v            # إيقاف مع حذف البيانات
```
ملفات التشغيل: `docker/Dockerfile.backend`، `docker/Dockerfile.frontend`، `docker/nginx.conf`،
`docker-compose.yml`، وللتسخّر أثناء التطوير `docker-compose.override.yml`.

### التشغيل المحلي بدون Docker
```bash
./scripts/dev.sh                  # الخلفية (uvicorn --reload) + الواجهة (npm run dev)
./scripts/dev.sh --backend-only   # الخلفية وحدها
./scripts/dev.sh --dry-run        # طباعة الأوامر دون تنفيذها
# Windows / PowerShell
.\scripts\dev.ps1 -BackendOnly -Port 8000
```

### توليد ملف `.env`
يتم توليد `.env` من `.env.example` تلقائيًا ضمن `scripts/setup.sh` و `scripts/setup.ps1` باستخدام بايثون. لا تُلزم `.env` أبدًا — إنها مستثناة من Git.

## نتيجة التحقق الفعلية
نتيجة بناء الحاويات وتشغيل السكربتات في بيئة التطوير موثّقة حرفيًا في
[`docs/ENVIRONMENT.md`](./docs/ENVIRONMENT.md) (القسم الثاني): Docker غير مثبت هناك،
لذا تم التحقق محليًا بالبدائل (فحص الصيغة، تحليل `nginx.conf` و`compose`، تشغيل `dev.sh` الفعلي مع uvicorn)،
وبُنيت الصورتان وشُغِّلا وتحقّق بقاء بيانات SQLite فعليًا في وظيفة CI `ops-docker` (حيث
Docker متوفر) — التفاصيل والنتائج في القسم الثاني من المستند.

## تنبيه مهم
المراحل **2 إلى 7 لم تُنفذ بعد**. هذا المستند والمخرجات المرتبطة خاصة بـ **المرحلة 1 فقط** ولا تمثل أي وظيفة تطبيقية مكتملة. لا تُبنى أي ميزة في هذه المهمة.
