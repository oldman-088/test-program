# NEXUS OSINT — fase 1: فحص البيئة وتأسيس هيكل المشروع

## نظرة عامة
نظام **NEXUS OSINT** هو منصة manage فريق من الموظفين الاصطناعيين (AI Agent Team Manager): مدير يحول التوجيهات إلى مهام، وعمال ينفذونها في فروع Git معزولة، ومراجع يراجع الطلبات قبل الدمج. يعتمد النظام على واجهة أمامية (React، AR/FA/EN) تتصل بواجهة خلفية (FastAPI)، مع أوكستراتور وجدولة ومزودي نماذج ومتصفح سواقة ولوحة قيادة.

## ما أُنجز في هذه المرحلة فقط (fase 1)
هذه المرحلة توثيقية وتأسيسية فقط. لا تُنفَّذ أي ميزة applicative، ولا تُحجب أي مهمة أخرى، ولا تعتمد على أي مهمة.

المخرجات التي أُضيفت في هذه المرحلة:
- `README.md` (هذا الملف) — نظرة عامة على NEXUS OSINT، ما أُنجز في fase 1 فقط، بنية المشروع، تعليمات تشغيل سريعة، وتنبيه بأن المراحل 2–7 لم تُنفذ بعد.
- `LICENSE` — رخصة MIT باسم صاحب المشروع (NEXUS OSINT Project Owner).
- `.gitignore` — يستثني `node_modules` و `dist` و `.venv` و `__pycache__` و `.pytest_cache` و `.env` و `*.sqlite3` و `.mypy_cache`.
- `docs/ENVIRONMENT.md` — نتائج فحص البيئة: النظام، والإصدارات، والأدوات المتاحة وغير المتاحة، والقيود.
- `docs/ROADMAP.md` — المراحل السبعة بالترتيب مع حالة كل مرحلة ومخرجاتها المتوقعة.
- `scripts/setup.sh` — نص برمجي لغرفة لينكس/ماك لإنشاء البيئة وتثبيت الاعتماديات وتوليد `.env`.
- `scripts/setup.ps1` — نص برمجي لبيئة PowerShell (ويندوز) لنفس الغرض.
- `tests/` — اختبارات آلية توكد وجود المخرجات وصلاحيتها.

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
├── backend/        (لم يُنشأ بعد — fase 2)
│   └── app/
│       ├── api/routes/
│       └── orchestration/
├── frontend/       (لم يُنشأ بعد — fase 7)
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
pip install -r backend/requirements.txt   # عند توفرها في fase 2

# تشغيل الخادم (عند توفر الكود)
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### الواجهة الأمامية (فرونت إند)
```bash
cd frontend
npm install
npm run dev
# عند توفر الكود في fase 7، يُشغل الخادم على http://localhost:3000
```

### توليد ملف `.env`
يتم توليد `.env` من `.env.example` تلقائيًا ضمن `scripts/setup.sh` و `scripts/setup.ps1` باستخدام بايثون. لا تُلزم `.env` कभी — إنها مستثناة من Git.

## تنبيه مهم
المراحل **2 إلى 7 لم تُنفذ بعد**. هذا المستند والمخرجات associée خاصة بـ **fase 1 فقط** ولا تمثل أي وظيفة applicative مكتملة. لا تُبنى أي ميزة في هذه المهمة.
