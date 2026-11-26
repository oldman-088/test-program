# فحص البيئة وتأسيس هيكل المشروع (المرحلة 1)

## ملخص تنفيذي
يستعرض هذا المستند نتائج فحص بيئة العمل لنظام **NEXUS OSINT** على المستودع `oldman-088/test-program`، ويسجّل الإصدارات والأدوات المتاحة وغير المتاحة والقيود التي يجب أن يعرفها باقي الفريق قبل البدء في المراحل التالية.

## معلومات الفحص
- تاريخ الفحص: 2026-11-26 (UTC)
- الجلسة: AATM-eca90c6e-a670-4150-9c8a-b38a05fd970a (Worker 5 — General Engineer)
- الفرع: `arena/11f4f537-test-program`، من `main` عند `3b5b04fe401ae22a3c19fe3e869427cbbb311c67`

## نظام التشغيل
- النظام: `Linux`
- المضيف: `e2b.local`
- النواة: `6.1.158+ #1 SMP PREEMPT_DYNAMIC Mon May 11 18:48:24 UTC 2026`
- البنية: `x86_64 GNU/Linux`

## الإصدارات المثبتة (الناتج الفعلي للأوامر)
| الأداة | الإصدار | الحالة |
|---|---|---|
| Python | 3.11.2 | متاح |
| pip | 23.0.1 | متاح |
| Node.js | v22.22.3 | متاح |
| npm | 10.9.8 | متاح |
| Git | 2.39.5 | متاح |
| Docker | غير مثبت | **غير متاح** |

تأكيد Docker (`docker --version`): الأمر غير موجود (`command not found`)، لذا Docker غير مثبت في هذه البيئة.

## الأدوات المتاحة وغير المتاحة
### متاح
- Python 3.11.2 مع pip
- Node.js 22.22.3 مع npm
- Git 2.39.5
- إنشاء بيئات افتراضية Python (`python3 -m venv`)

### غير متاح / مقيد
- **Docker غير مثبت** — لا يمكن بناء أو تشغيل حاويات Docker في هذه البيئة. أي مرحلة تعتمد على Docker (مثل Postgres/RabbitMQ/Redis عبر حاويات) ستتطلب توفير Docker خارجيًا أو الاعتماد على SQLite محليًا في المرحلة 1.
- لا يوجد مدير حزم Python مثل `poetry` أو `pipenv` مثبتًا افتراضيًا (يُستخدم `venv` + `pip`).

## القيود التي يجب أن يعرفها الفريق
1. Docker غير متاح، لذا لا يمكن الاعتماد على خدمات الحاويات في المرحلة 1؛ يُستخدم SQLite كقاعدة بيانات افتراضية مؤقتة حتى تُوفَّر البنية التحتية لاحقًا.
2. المستودع فارغ تقريباً (يحتوي فقط على `README.md` أولية) — لا يوجد كود تطبيق خلفي أو واجهة أمامية بعد؛ المراحل 2 إلى 7 لم تُنفذ.
3. جميع التعليمات والنصوص البرمجية في هذه المرحلة توثيقية وتأسيسية فقط ولا تُحجب أي مهمة أخرى ولا تعتمد على أي مهمة.
4. لا تُدرج أي أسرار أو مفاتيح فعلية في `.env`؛ يُستخدم `.env.example` كقيمة مثال وتُولَّد `.env` عبر السكريبتات.

---

# القسم الثاني — التشغيل بالحاويات وسكربتات التطوير المحلي (المهمة AATM-c740feee)

- تاريخ الفحص والتحقق: 2026-11-26 (UTC)
- الجلسة: AATM-c740feee-a5ee-4519-958f-93dbc7b1241a (Worker 5 — General Engineer)
- الفرع: `arena/82fdba0c-test-program`، من `main` عند `cbc9c69483d7ed7705fd4eba79ab2fbcd57c8219`

## المخرجات التي أُضيفت في هذه المهمة
| الملف | الدور |
|---|---|
| `docker/Dockerfile.backend` | صورة الخلفية من `python:3.12-slim`، تثبيت `backend/requirements.txt`، تشغيل `uvicorn` على `0.0.0.0` بمنفذ من متغير البيئة `BACKEND_PORT` (افتراضيًا 8000)، مستخدم غير جذري، `HEALTHCHECK` قابل للتهيئة |
| `docker/Dockerfile.frontend` | بناء بـ `node:20-alpine` ثم خدمة `frontend/dist` بـ `nginx:alpine`؛ هدف إضافي `dev` لخادم تطوير الواجهة |
| `docker/nginx.conf` | خدمة الملفات الثابتة + توجيه `/api` و `/ws` إلى خدمة الخلفية `backend:8000` + `SPA fallback` + `/healthz` |
| `docker-compose.yml` | خدمتا `backend` و `frontend`، `env_file: .env`، `volume` مُسمّى `nexus-osint-data` لمجلد قاعدة البيانات، منافذ منشورة |
| `docker-compose.override.yml` | تسخّر الكود أثناء التطوير (bind mounts + `UVICORN_RELOAD=1` + هدف `dev`) |
| `.dockerignore` | إخراج `.env` و `.git` و `node_modules` و `dist` من سياق البناء |
| `scripts/dev.sh`, `scripts/dev.ps1` | تشغيل الخلفية والواجهة محليًا **بدون Docker** |
| `tests/test_ops_containers.py` | اختبارات بنيوية + تحليل Compose + اختبار تكامل حقيقي عند توفر Docker |
| `.env.example`, `.gitignore`, `pytest.ini`, `.github/workflows/ci.yml` | مفاتيح نشر الحاويات، استثناء مخلفات التشغيل، وسم `integration`، ووظيفة CI للتحقق بالحاويات |

## نتيجة البناء الفعلية
**لم يُنفَّذ بناء صور فعلي في بيئة العمل هذه: Docker غير مثبت وغير متوفر.** هذا تصريح
بما حدث، لا تفسير بديل. الناتج الحرفي لأوامر الفحص:

```console
$ docker --version
/bin/bash: line 1: docker: command not found
exit=127
$ docker compose version
/bin/bash: line 1: docker: command not found
exit=127
$ for c in podman nerdctl buildah docker-compose nginx pwsh shellcheck; do command -v $c || echo MISSING; done
podman -> MISSING   nerdctl -> MISSING   buildah -> MISSING
docker-compose -> MISSING   nginx -> MISSING   pwsh -> MISSING   shellcheck -> MISSING
```

وبما أن `docker compose build` و `docker compose up` لا يمكن تشغيلهما هنا، فإن
التحقق من ملفاتي تمّ بثلاث طبقات بديلة، كلها بأوامر حقيقية:

1. **فحص الصيغة النحوية**: `bash -n scripts/dev.sh` (نجح)، وموازنة أقواس
   `docker/nginx.conf`، وتحليل `docker-compose.yml` و `docker-compose.override.yml`
   بـ PyYAML: `OK services: ['backend', 'frontend']` للملفين.
2. **تشغيل فعلي بلا حاويات**: `scripts/dev.sh --dry-run` يطبع الأوامر الحقيقية، ثم
   تشغيل فعلي لـ `uvicorn` على المنفذ المحلي مع اختبار الاستجابة والتنظيف:
   ```console
   $ bash scripts/dev.sh --dry-run --host 127.0.0.1 --port 8137
   ==> الخلفية: تحضير بيئة بايثون...
   ==> الخلفية ستعمل على http://127.0.0.1:8137/api  (APP_IMPORT=backend.app.main:app)
   [dry-run] uvicorn 'backend.app.main:app' --host '127.0.0.1' --port '8137' --reload --reload-dir '<root>/backend'
   ==> dry-run اكتمل — لم تُشغَّل أي عملية.
   ```
   وفي التشغيل الحقيقي (نسخة مؤقتة فيها `backend/app/main.py` بديل) استجابت الخلفية
   `200 OK` على `http://127.0.0.1:8391/api/health`، وعند `SIGTERM` أُغلقت الخلفية
   والمنفذ ولم تبقَ عملية يتيمة.
3. **فحص صيغة ملفات الحاويات بأدوات حقيقية** (بلا Docker):
   - `docker/nginx.conf` بمحلّل قواعد nginx (حزمة `crossplane`) بعد لفّه في سياق `http{}`:
     النتيجة `status: ok` و `errors: []`، والمواقع المحلَّلة `= /healthz` و `^~ /api/` و
     `^~ /ws/` و `~* \.(js|css|…)$` و `~ /\.` و `/`.
   - `docker/Dockerfile.backend` و `docker/Dockerfile.frontend` بحزمة `dockerfile-parse`:
     صور الأساس المقروءة `[python:3.12-slim]` و `[node:20-alpine, nginx:alpine, node:20-alpine]`
     مع سلاسل ENV/LABEL/CMD مقروءة — أي أن استمرارات الخط الساطع واقتباسات JSON صالحة.
4. **اختبارات آلية** في `tests/test_ops_containers.py`: الناتج الفعلي في هذه البيئة
   `60 passed, 6 skipped` (التخطّي لغياب `pwsh` و Docker)، و 5 اختبارات
   مُخصصة لبيئة فيها Docker (تحليل `docker compose config`، ثم بناء الصور وتشغيلها) — **نجحت جميعها في CI**
   كما هو موثّق أدناه تحت «نتيجة البناء الفعلية في بيئة فيها Docker».

### أوامر التحقق المطلوبة على مضيف فيه Docker
لم يُتحقَّق من هذا في بيئة العمل (Docker غير مثبت، انظر ما سبق)، وهو ما تشغّله وظيفة
CI `ops-docker` بالنيابة. على أي مضيف فيه Docker و Compose v2، المتسلسل الكامل هو:

```console
$ cp .env.example .env
$ docker compose config --quiet          # يفحص docker-compose.yml ودمج override
$ docker compose build                   # docker/Dockerfile.backend + docker/Dockerfile.frontend
$ docker compose up -d --wait
$ curl -fsS http://localhost:3000/ | head -5             # الواجهة من nginx على منفذ منشور
$ curl -fsS http://localhost:3000/api/health            # /api يمرّ إلى الخلفية عبر nginx
$ curl -fsS http://localhost:8000/api/health            # الخلفية مباشرة
$ docker compose exec backend python -c "import glob;print(glob.glob('/app/data/*'))"   # nexus.db في الـ volume
$ docker compose down && docker compose up -d --wait    # البيانات باقية: nexus-osint-data volume
$ docker compose down -v                                # هنا فقط تُمسح قاعدة البيانات
```

والبديل بلا حاويات هو `scripts/dev.sh` (أو `scripts/dev.ps1` على Windows) كما في القسم
التالي. ملاحظة: نجاح `docker compose build` و `docker compose up` مشروط بدمج مخرجات
المهام 1–3 (انظر الجدول أدناه)، لا بملفات هذه المهمة وحدها.

### ما لم يكتمل ولماذا (حالة صريحة)
- **بناء وتشغيل الصورتين (`docker compose up`) غير متحقق محليًا** — لا Docker في البيئة.
  التحقق منه مُوكَل إلى وظيفة CI `ops-docker` المضافة في `.github/workflows/ci.yml`،
  التي تشغّل مجموعتي على `ubuntu-latest` حيث Docker و Docker Compose متوفران:
  `docker compose config` لفحص الصيغة، ثم `pytest -m integration` بـ `NEXUS_RUN_DOCKER_INTEGRATION=1`
  للبناء والتشغيل الفعليين: تبني
  الصورتين، ترفع Stack، تتحقق أن الواجهة تُخدم على منفذ منشور، أن `/api` يصل إلى
  الخلفية، وأن صفّ SQLite المكتوب في الـ volume يبقى بعد `docker compose down` ثم
  `up`. الاختبارات: `test_docker_compose_up_serves_frontend_proxies_api_and_persists_sqlite`.
- **لا يمكن بناء الصورتين من `main` الآن حتى مع Docker متاح**، لأن هذه المهمة تفتح بعد
  مهام لم تُدمج بعد: `main@cbc9c69` لا يحتوي `backend/` ولا `frontend/` إطلاقًا (المحتوى
  الحالي مخرجات المرحلة 1 التأسيسية فقط). ملفا Dockerfile مكتوبان على العقد المعلن في
  تلك المهام، ويفشل البناء برسالة واضحة حتى توافرها:

  | ما تحتاجه الصورة | المسار المطلوب | من يملكه |
  |---|---|---|
  | `docker/Dockerfile.backend` | `backend/requirements.txt` + `backend/app/main.py` يصدّر `app` | مهمة النواة الخلفية (1) |
  | قاعدة بيانات SQLite | `DATABASE_URL` (يُثبَّته Compose على `sqlite:////app/data/nexus.db`) | مهمة قاعدة البيانات (2) |
  | `docker/Dockerfile.frontend` | `frontend/package.json` مع `scripts.build` يُنتج `dist/` و `scripts.dev` | مهمة الواجهة (3) |

- **قيد في الحوكمة**: نصّ المهمة أرفق prefight بقيمة `main` متوقعة
  `1da237fee8ee5e6abacfc8a5402effa9af4568c6`، بينما `origin/main` فعليًا عند
  `cbc9c69483d7ed7705fd4eba79ab2fbcd57c8219` (وهو نفس الـ SHA الذي فُرِع منه هذا العمل؛
  الـ SHA المتوقع غير موجود في المستودع إطلاقًا — `git cat-file` يفشل و `api.github.com`
  يرجع 422). سُجّل ذلك في تقرير AATM عند التعثر، وتم الإكمال بعد تأكيد الأساس.

## تعليمات بديلة (بلا Docker)
```bash
# 1) نفس ما يفعله setup.sh: توليد .env من .env.example إن لزم
# 2) تشغيل الخلفية والواجهة محليًا بدون أي حاويات
./scripts/dev.sh                 # الخلفية + الواجهة معًا
./scripts/dev.sh --backend-only  # الخلفية فقط (uvicorn --reload)
./scripts/dev.sh --dry-run       # طباعة الأوامر دون تنفيذها

# PowerShell / Windows
.\scripts\dev.ps1 -DryRun
.\scripts\dev.ps1 -BackendOnly -Port 8000
```
الأداة تتجاهل المكوّن غير الموجود برسالة واضحة بدل الفشل الصامت، وترفض أي وسيط
مجهول، وتقرأ `.env` بتحليل سطور آمن (لا `source` ولا `Invoke-Expression`) لأن قيمًا مثل
`APP_NAME=NEXUS OSINT` تُفسَّر كأمر عند `source`.

### نتيجة البناء الفعلية في بيئة فيها Docker (وظيفة CI `ops-docker`)
Docker غير متوفر في بيئة العمل المحلية، لذلك نُفِّذ البناء والتشغيل في CI على
`ubuntu-latest` (والوظيفة خضراء على هذا الطلب). الناتج الحرفي من تعليمة `::notice::`
التي تنشر ملخص pytest في آخر خطوة:

```console
ops-docker: 50 passed, 1 skipped in 30.15s
SKIPPED [1] tests/test_ops_containers.py:535: uvicorn غير مثبت في بيئة الاختبار
```

المُثبَت آليًا هناك (وليس بالادعاء):
- `docker compose config --quiet` نجح على `docker-compose.yml` وعلى دمجه مع
  `docker-compose.override.yml` — من جذر المستودع نفسه رغم غياب `backend/` و `frontend/`.
- `docker compose build` بنى الصورتين من `docker/Dockerfile.backend` و
  `docker/Dockerfile.frontend` (نماذج `backend/` و `frontend/` مؤقتة في الدليل
  المؤقت للاختبار فقط).
- `docker compose up -d --wait`: الحاوية الخلفية `healthy` والأمامية `healthy`.
- الواجهة تُخدم على منفذ منشور عبر nginx (index + `app.css` + `SPA fallback`)،
  و `/api/health` يمرّ إلى خدمة `backend:8000`، والخلفية تجيب على منفذها المنشور.
- صف SQLite المكتوب عبر `/api/db/hit` بقي بعد `docker compose down` ثم `up`
  (`nexus-osint-data`)، و`nexus.db` وُجد داخل `/app/data`، والحاوية الخلفية لا تعمل
  بالجذر (`id -u` = 10001).
- `docker-compose.override.yml` يبدّل الواجهة إلى هدف `dev` ويخدم خادم التطوير
  على نفس المنفذ المنشور.
- اختبارا `scripts/dev.ps1` مع `pwsh` الحقيقي: تحليل نحو dry-run نجحا.
- الاختبار `test_backend_healthcheck_command_actually_works` ينفّذ أمر `HEALTHCHECK` الحرفي من الـ Dockerfile مقابل خادم صلاحي (محليًا وفي CI).

الوظيفة تنشر هذا الملخص كـ annotation لأن سجلات runner لا تُقرأ من بيئات العمل المعزولة
هنا (المضيف الخارجي الوحيد المسموح هو `api.github.com`).

### ما كشفته أول تشغيل فعلي لوظيفة CI `ops-docker`
سجّل أول تشغيل حقيقي (runner فيه Docker) ما يلي — وهو بالضبط سبب إضافة هذه الوظيفة:

| ما تحقق | النتيجة |
|---|---|
| `docker compose config --quiet` (الملف الأساسي + دمج override) في جذر المستودع | نجح، رغم غياب `backend/` و `frontend/` |
| بناء `docker/Dockerfile.backend` و `docker/Dockerfile.frontend` | نجح البناءان (نموذج backend/frontend مؤقت في الدليل المؤقت للاختبار فقط) |
| حالة حاوية الواجهة بعد `up` | `healthy` — أي أن `docker/nginx.conf` صالح تشغيليًا و`/healthz` يعمل |
| حالة حاوية الخلفية | `unhealthy` في أول تشغيل: خطأ أولوية في بناء رابط الفحص (`'…:'+X or '8000'+p` بدل `'…:'+(X or '8000')+p`) فصار الرابط بلا مسار → 404 |
| ما فُعل بعد ذلك | أُصلح السطر، وأُضيف `test_backend_healthcheck_command_actually_works` يقرأ أمر `HEALTHCHECK` من ملف Dockerfile نفسه وينفّذه مقابل خادم صلاحي: ينجح على `${API_PREFIX}/health`، ويفشل على 404 (لا نجاح زائف)، ويحيّد نفسه عند `HEALTHCHECK_PATH=""` |

## قرارات تصميم يجب معرفتها
- **منفذ الخلفية**: `BACKEND_PORT=8000` مثبّت داخل شبكة Compose ليطابق `backend:8000`
  في `nginx.conf`؛ ما يتغيّر على المضيف هو `BACKEND_HOST_PORT` (من `.env`).
- **البيانات**: `nexus-osint-data` volume باسم ثابت مُركَّب على `/app/data`؛ لذلك
  `docker compose down` يحفظ البيانات، و `docker compose down -v` يمسحها. لا تُكتب
  القاعدة داخل الصورة.
- **`/api` يمر كما هو** (لا `rewrite`)، أي أن الخلفية يجب أن تركّب موجّهاتها تحت
  `API_PREFIX=/api`. إن اختارت مهمة النواة مسارًا جذريًا بدون بادئة، فالتعديل في
  `docker/nginx.conf` بسطر `rewrite ^/api/(.*) /$1 break;` داخل `location ^~ /api/`.
- **فحص الصحة**: `HEALTHCHECK_PATH` (افتراضيًا `/api/health`). عطّله بـ
  `HEALTHCHECK_PATH=""` إن لم يكن المسار موجودًا بعد، وإلا ستبقى الحاوية `unhealthy`
  ويتعذّر `docker compose up --wait`.
- **الإقلاع قبل جاهزية الخلفية**: `nginx.conf` يستخدم `resolver 127.0.0.11` مع
  متغيّر في `proxy_pass` ليحلّ اسم الخدمة وقت الطلب؛ البديل الحرفي
  `proxy_pass http://backend:8000;` يفرض أن تكون الخلفية تعمل قبل nginx.
- **وضع التطوير لا يعرّف `ports`**: قوائم Compose تُدمج مع الملف الأساسي، وأي إضافة
  هناك تسبب تعارضًا على منفذ المضيف؛ يُعاد استخدام نفس النشر مع خادم تطوير يستمع على
  8080 داخل الحاوية. الواجهة يجب أن تستخدم `/api` و `/ws` نسبيًا (قاعدة AGENTS 6)،
  ويحتاج خادم التطوير إلى proxy إلى `http://backend:8000` — إجراء على ملك مهمة الواجهة.
- **الأمان**: لا أسرار في الصور أو ملفات Compose (تُمرَّر عبر `.env` المستثنى من Git)،
  والخلفية تعمل بمستخدم غير جذري (`uid 10001`).

## إصدارات البيئة المعاد قياسها في هذه المهمة
| الأداة | الإصدار | الحالة |
|---|---|---|
| Python | 3.11.2 | متاح |
| Node.js | v22.22.3 | متاح |
| npm | 10.9.8 | متاح |
| Git | 2.39.5 | متاح |
| Docker / Compose | — | **غير مثبت** |
| podman / nerdctl / buildah | — | غير متوفر |
| pwsh (PowerShell) | — | غير متوفر (اختبارات `dev.ps1` تُتخطّى محليًا وتعمل في CI عند توفره) |
| shellcheck | — | غير متوفر |
