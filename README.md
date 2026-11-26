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

### توليد ملف `.env`
يتم توليد `.env` من `.env.example` تلقائيًا ضمن `scripts/setup.sh` و `scripts/setup.ps1` باستخدام بايثون. لا تُلزم `.env` أبدًا — إنها مستثناة من Git.

## تنبيه مهم
المراحل **2 إلى 7 لم تُنفذ بعد**. هذا المستند والمخرجات المرتبطة خاصة بـ **المرحلة 1 فقط** ولا تمثل أي وظيفة تطبيقية مكتملة. لا تُبنى أي ميزة في هذه المهمة.

---

## وثائق التقييم (docs only)

| الوثيقة | المحتوى |
| --- | --- |
| [`docs/INTEGRATIONS_EVALUATION.md`](./docs/INTEGRATIONS_EVALUATION.md) | تقييم أدوات OSINT: Sherlock · Maigret · PhoneInfoga · OpenOSINT · Holehe |
| [`docs/AATM_ARENA_EVALUATION.md`](./docs/AATM_ARENA_EVALUATION.md) | تقييم مستودع AATM وموصل Arena، وتصميم وحدة `NEXUS Arena Bridge` ومحوّل `AATM Integration Adapter` الاختياريين (تصميم غير منفّذ) |

اختبارات عقود الوثائق (بلا أي حزمة خارجية):

```bash
python3 -m unittest tests.test_aatm_arena_evaluation -v   # 28 اختباراً، stdlib فقط
python -m pytest tests/ -v                                # الحزمة الكاملة (ما يشغّله CI)
```

> `tests/manual/probe_aatm_connector.py` أداة أدلة يدوية (لا تُجمع مع الاختبارات): وجّه
> `AATM_REPO` إلى نسخة AATM لإعادة إنتاج القياسات المذكورة في `docs/AATM_ARENA_EVALUATION.md`.
