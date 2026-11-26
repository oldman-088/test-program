# تقييم مستودع AATM وموصل Arena — AATM & Arena Connector Evaluation

**المهمة:** `AATM-c4e0aae6-519f-424d-b8dd-424634ff64d6` — بحث وتوثيق فقط.
**المستودع المدروس:** `https://github.com/oldman-088/AATM`
**الالتزام المقروء (commit):** `1da237fee8ee5e6abacfc8a5402effa9af4568c6` (2026-11-25، `Merge pull request #107`)، الفرع الافتراضي `main`.
**تاريخ الفحص:** 2026-11-26 (UTC).
**النطاق:** لا يوجد — ولا يُضاف — أي كود تكامل في هذا المستودع نتيجةً لهذا الملف. لا وحدة `NEXUS Arena Bridge` ولا محوّل `AATM Integration Adapter` منفّذان هنا؛ ما يلي تصميم مقترح + تقييم مبني على قراءة الشيفرة وقياس محدود موضّح أدناه.

> ### منهجية التحقق (ثلاث درجات فقط، ولا رابع)
> 1. **مقروء من المصدر** — كل عبارة تحمل مسار ملف وسطر/دالة تُقرأ فعلياً في الالتزام `1da237f`. هذا هو مصدر أغلب ما يلي.
> 2. **مُتحقَّق بالتنفيذ** — نتائج تشغيل فعلي لِـ `bridge/connector.py` و`bridge/server.py` في بيئة معزولة (Python 3.11، `fastapi 0.165.0`، `pydantic 2.14.4`، `httpx 0.28.1`، `pytest 9.2.0`) عبر سكربت الفحص المرفق `tests/manual/probe_aatm_connector.py`. النتائج في §15.
> 3. **غير متحقق (unverified)** — موسوم صراحةً بعبارة **«غير متحقق»**: كل ما يتعلّق بسلوك موقع Arena الحقيقي، وبصفحة الإنتاج، وبأي تشغيل فعلي لأدوات AATM الكاملة (خادم + قاعدة بيانات + Chrome + Tampermonkey + `arena.ai`)، وبأي تكامل بين AATM وNEXUS OSINT. **لا يوجد أي تكامل بين AATM وNEXUS، ولم يُختبر أي تكامل، ولا يُدّعى أنه يعمل.**

> ### الحكم النهائي في سطر واحد
> موصل Arena في AATM **قابل لإعادة الاستخدام كمَرجع معماري ونمط تصميم** (بروتوكول الرسائل، فصل الجسر عن الخلفية، بوابة التشغيل، حالة `needs_human`، تدقيق السكربت قبل التسليم) — **وغير قابل لإعادة الاستخدام ككود** في هذه المرحلة لسببين حاسمين: (1) المستودع **بلا ترخيص** (`license: null` في GitHub API، ولا ملف `LICENSE` في الجذر) فلا يوجد أي منح حقوق لنسخ الشيفرة أو اشتقاقها؛ (2) الشيفرة مشدودة إلى نموذج بيانات AATM (SQLAlchemy `BrowserProfile` / `Agent` / `ArenaSession`) وإلى `app.core.config.get_settings()`. البديل المعتمد في هذا الملف: **إعادة تنفيذ مستقلة ومتوافقة مع البروتوكول** (§17) داخل وحدة اختيارية، لا نسخ ولا توريث.

---

## 0. جدول المطابقة مع بنود المهمة

نصّ المهمة يسمّي **اثني عشر جانباً**، وقائمة القبول تذكر **أحد عشر بنداً** دون تحديد البند المُسقَط. لتغطية القراءتين، وُثِّق **الاثنا عشر جميعاً** في الأقسام §2–§13، وهو ما يغطّي الأحد عشر بأي قراءة.

| # | الجانب المطلوب في المهمة | القسم | المسارات/الدوال المسمّاة |
| --- | --- | --- | --- |
| 1 | البنية العامة | §2 | `backend/app/`, `bridge/`, `frontend/`, `contracts/` |
| 2 | إدارة الوكلاء | §3 | `orchestration/scheduler.py::TaskScheduler`, `browser/arena_sessions.py::set_arena_mode` |
| 3 | موصل المتصفح (browser connector) | §4 | `browser/arena_connector.py`, `bridge/connector.py::ConnectorHub` |
| 4 | تكامل Arena | §5 | `backend/app/providers/adapters/arena_browser.py`, `arena_agent.py`, `arena_bridge.py` |
| 5 | الجسر المحلي (local bridge) | §6 | `bridge/server.py::create_app`, `_verify_bearer_auth` |
| 6 | تنفيذ userscript أو الإضافة | §7 | `build_userscript()`, `USERSCRIPT_BODY`, `validate_userscript_policy()` |
| 7 | إدارة ملفات تعريف المتصفح | §8 | `browser/manager.py::BrowserManager`, `models/…BrowserProfile` |
| 8 | نقل الرسائل (transport) | §9 | `WS /v1/connector`, `POST /v1/chat/completions`, `PUT /v1/connector/profiles/{id}` |
| 9 | تقرير حالة الاتصال | §10 | `ProfileState.summary()`, `GET /api/v1/arena/connector/status` |
| 10 | الإعدادات | §11 | `core/config.py` (`ARENA_*`), متغيّرات بيئة الجسر |
| 11 | معالجة الأخطاء | §12 | `ConnectorError`, `ArenaNotEnabled`, `ArenaAgentError` |
| 12 | نموذج الأمان | §13 | `safety.py`, `engines.py`, `mint_token()`, `docs/SECURITY.md §8` |

البنود الإضافية المطلوبة صراحةً في نصّ المهمة تُغطّى في: §14 (قابلية إعادة الاستخدام)، §16 (تدفق المصادقة اليدوي)، §17 (حالات الاتصال المطلوبة)، §18 (القيود الإلزامية)، §19 (وحدة `NEXUS Arena Bridge`)، §20 (محوّل `AATM Integration Adapter`)، §21 (استقلال النواة).

---

## 1. بيانات المستودع (من GitHub API + الاستنساخ)

| البند | القيمة |
| --- | --- |
| الاسم | `oldman-088/AATM` (عام / public) |
| الترخيص | **لا يوجد** — `license: null`، ولا `LICENSE` في الجذر. يوجد `THIRD_PARTY_NOTICES.md` (إشعارات طرف ثالث فقط) |
| إنشاء | 2026-11-15 · آخر push: 2026-11-25 |
| الالتزام الأخير | `1da237fe` — 2026-11-25 (PR #107) |
| حجم الشيفرة | ~59,867 سطر Python في `backend/` + `bridge/` (عدّ `wc -l`) |
| الاختبارات | **91** ملف اختبار في `backend/tests/` + `bridge/tests/test_bridge.py` |
| CI | `.github/workflows/ci.yml` — وظيفة واحدة: Alembic، Ruff، `pytest` للـ backend، `pytest` للجسر، ماسح أسرار، tsc/vitest/build للواجهة |
| النجوم | 0 (غير متحقق كدلالة على الجودة — المشروع حديث خاص بمالكه ومهامه) |

**ملاحظة ترخيص حاسمة:** غياب `LICENSE` يعني أن حقوق النسخ والاشتقاق غير ممنوحة صراحةً. `THIRD_PARTY_NOTICES.md` يوثّق أن جسم السكربت المُولَّد **مشتق** من مشروع MIT خارجي (`arena-auto-continue` لأنور كومار نيشاد) — وهذا يورّث التزامات إشعار للمشروع الأصلي، لا يمنح AATM نفسه ترخيصاً.

---

## 2. البنية العامة

```
backend/app/
  api/routes/        arena.py · platform.py · platform_browsers.py · platform_employees.py · dashboard.py …
  browser/           arena_connector.py · arena_sessions.py · manager.py · engines.py · safety.py
                     capabilities.py · install_links.py · wall.py
  orchestration/     scheduler.py · arena_runner.py · arena_prompts.py · manager_arena.py
                     merge_queue.py · review.py · replacement.py · autoscale.py · self_heal.py
  providers/         router.py · base.py · adapters/{arena_browser,arena_agent,arena_bridge,__init__}.py
  runtime/           agent_loop.py · loop/{claim,actions,approvals}.py · sandbox.py · agent_protocol.py
  core/config.py     كل الإعدادات (pydantic-settings)
  employees/catalog.py · models/ · schemas/ · qa/engine.py
bridge/              server.py · connector.py · mock_arena/{index,agent}.html · tests/
frontend/src/views/  ArenaViews.tsx
docs/                SECURITY.md · SETUP_AR.md · ARCHITECTURE.md · AATM_ARENA_AGENT_PROMPT.md
```

فصل الطبقات نظيف وقابل للقراءة:
- **الخلفية** (`backend/app`) تملك السياسة: البوابات، توليد السكربت، تسجيل الملفات، الجلسات، الجدولة، التدقيق.
- **الجسر** (`bridge/`) يملك النقل: عملية مستقلة على `127.0.0.1:4100`، لا يعرف قاعدة البيانات ولا SQLAlchemy (تحقّقتُ: `bridge/*.py` لا تستورد `app.*` إلا في الاختبارات).
- **المتصفح** لا يُدار برمجياً للـ Arena: `BrowserManager.run_userscript()` ترفع HTTP **501** دائماً؛ الحقن البرمجي للسكربت ممنوع بالتصميم.

عائق إعادة الاستخدام الأول: منطق Arena **موزّع لا محزوم**. عدّ فعلي على الالتزام `1da237f`: `grep -rli arena backend/app --include=*.py` يطابق **39 ملفاً** في `backend/app` وحده، منها `browser/` و`providers/adapters/` و`api/routes/` و`orchestration/` و`runtime/`. أي أن "الموصل" ليس حزمة واحدة قابلة للسحب، بل **سلوك موزّع** عبر التطبيق — وهذا أهم عائق هندسي أمام إعادة الاستخدام كوحدة (منفصل عن عائق الترخيص).

---

## 3. إدارة الوكلاء

| المكوّن | المسار/الدالة | ملاحظات |
| --- | --- | --- |
| جدولة المهام والالتقاط الذرّي | `backend/app/orchestration/scheduler.py::TaskScheduler.run_orchestration_cycle`, `acquire_lock`, `release_lock` | قفل على مستوى المهمة + تحقق من التبعيات (`dependencies_satisfied`) ومن الدورات (`_has_cycle`) |
| تجنّب إرسال مهمة لعامل غير متصل | `scheduler.py::_arena_disconnected_agent_ids` | عندما يكون Arena مفعّلاً و`bridge_call("GET","/v1/connector/profiles")` يفشل، **يُعامَل كل عامل له ملف كأنه غير متصل** فلا تُرسَل له مهمة |
| تحويل موظف إلى وكيل Arena | `browser/arena_sessions.py::set_arena_mode` | يغيّر `profile.arena_mode` بين `chat` و`agent`، يكتب `AuditLog(action="arena.mode_changed")`، ثم يعيد التسجيل في الجسر |
| التبديل الجماعي | `api/routes/arena.py::set_all_agents_mode` | `PUT /api/v1/arena/agents/mode` |
| جلسة لكل (موظف، مهمة) | `arena_sessions.py::claim_session` | جلسة واحدة مفتوحة لكل ملف؛ جلسة مهمة أخرى نشطة = `ArenaSessionConflict` (تبويب واحد يقود جلسة واحدة) |
| دورة حياة المهمة عبر المتصفح | `orchestration/arena_runner.py` (1,311 سطر) | `new_session → submit → مراقبة الحالات → keep_working → read_last_reply → create_pr → review` |
| إدارة المدير | `orchestration/manager_arena.py` (1,656 سطر) | مدير له ملف Arena خاص (`MANAGER_AGENT_ID="manager-0"`، `MANAGER_PROFILE_ID="profile-manager"`) |
| التعافي والاستبدال | `orchestration/self_heal.py`, `replacement.py` | `ReplacementAndEmergencyService._cleanup_bridge_session()` ينادي `delete_session()` على الجسر |

نمط مفيد للنقل: **حالة الموصل تدخل في قرار الجدولة**. AATM لا يحاول إرسال مهمة ثم يفشل؛ يمنع الإرسال مسبقاً. هذا النمط يستحق التقليد في NEXUS (انظر §19 و§23).

---

## 4. موصل المتصفح (browser connector)

الموصل نصفان لا نصف واحد:

### 4.1 نصف الخلفية — `backend/app/browser/arena_connector.py` (1,284 سطر)

| الدالة | الدور |
| --- | --- |
| `arena_gate()` | يعيد `{"mode": "real"|"mock"|"disabled", "enabled", "real_enabled", "allowed_origins", "mock_url", "agent_new_session_url", "code", "message"}` — كل مسار حقيقي يبدأ من هنا |
| `real_arena_enabled()` | `ARENA_CONNECTOR_ENABLED` **و** وجود أصل واحد صالح في `ARENA_ALLOWED_ORIGINS` (الاثنان معاً) |
| `configured_origins()` | يقرأ `ARENA_ALLOWED_ORIGINS` ويحوّل المضيف العاري إلى `https://` |
| `allowed_origins()` / `match_patterns()` | أصول مسموحة + أنماط `@match` للسكربت (mock + real) |
| `mock_url()` | يقبل `ARENA_MOCK_URL` **فقط** إذا كان loopback (حماية من "mock" يشير لموقع حقيقي) |
| `bridge_ws_url()` | يحوّل `ARENA_BRIDGE_URL` إلى `ws(s)://…/v1/connector` |
| `mint_token(profile)` | `secrets.token_urlsafe(32)`؛ يخزّن **SHA-256 فقط** في `profile.connector_token_hash` + `connector_token_rotated_at` |
| `build_userscript(profile, agent, token)` | يولّد السكربت: ترويسة `// ==UserScript==` مع `@match` لكل نمط، `@grant none`، `@run-at document-idle`، `@noframes`، ثم `USERSCRIPT_BODY` |
| `register_profile_with_bridge(profile, dom=…)` | `PUT {ARENA_BRIDGE_URL}/v1/connector/profiles/{id}` مع `token_sha256` و`allowed_origins` و`real_enabled` و`mode` و`new_session_url` و`dom` |
| `bridge_call(method, path, body, timeout=10)` | عميل HTTP موحّد للجسر؛ يعيد `{"ok": False, "code", "message"}` بدل رفع استثناء |
| `ensure_arena_browser_provider(db)` | ينشئ صف `AIProvider(id="arena-browser", provider_type="arena_browser", credential_ref="env:ARENA_BRIDGE_TOKEN")` مرة واحدة (مع معالجة `IntegrityError` للتزامن) |
| `require_real_arena()` | حارس لكل مسار حقيقي؛ يرفع `ArenaNotEnabled` |

ثابتان مهمان: `SCRIPT_VERSION = "2.3.1"` و`NOT_ENABLED_MESSAGE` (رسالة موحّدة تُعاد لكل مسار معطّل: `not_enabled`, HTTP 409).

### 4.2 نصف الجسر — `bridge/connector.py` (748 سطر)

`ConnectorHub` هو السجل الحقيقي: `register()`, `unregister()`, `reset()`, `handle_socket()`, `_authenticate()`, `_on_message()`, `_mark_needs_human()`, `dispatch()`, `command()`, `_validate_command()`, `summaries()`, بالإضافة إلى `register_connector_routes(app, hub)` الذي يسجّل مسارات الـ WebSocket والإدارة.

- `ProfileState` يحفظ: `token_hash`, `allowed_origins`, `real_enabled`, `mode`, `new_session_url`, `dom`, `stop_selectors`, `stop_phrases`, `status`, `needs_human_reason`, `agent_state`, `last_error`, `selector_report`, `requests_total`, `commands_total`, `events` (حلقة 50 حدثاً).
- قفل واحد لكل ملف: `async with state.lock` في `dispatch()` و`command()` = **طلب/أمر واحد في وقت واحد لكل تبويب**.
- `AGENT_COMMANDS` = 9 أوامر محصورة: `new_session, submit, keep_working, stop, read_last_reply, selector_test, select_repo, create_pr, close_feedback`. أي أمر خارجها → `unknown_command` / HTTP 422.
- `READ_ONLY_COMMANDS = ("read_last_reply","selector_test")` و`SAFE_STOP_COMMANDS = ("stop",)` — تُسمح وهي في حالة توقّف (اقرأ §13.4).
- استمرارية اختيارية: `_load()`/`_save()` إلى `AATM_BRIDGE_STATE_FILE` بصلاحية `0600` وكتابة ذرّية عبر `os.replace`، ولا تُحفظ أي أسرار (فقط التجزئة والتسجيل و`needs_human_reason`).

---

## 5. تكامل Arena في طبقة المزوّدين

| المحوّل | المسار | الوظيفة |
| --- | --- | --- |
| `ArenaBrowserAdapter` | `backend/app/providers/adapters/arena_browser.py` (130 سطر) | وضع "chat": رسالة واحدة → جواب واحد عبر `POST {ARENA_BRIDGE_URL}/v1/chat/completions` بالحقل `model="arena_browser"` وترويسة `X-AATM-Profile-Id`. `health_check()` يعدّ الملفات بحالة `ready`. `dry_run` يفشل بـ `dry_run`. **لا يعيد المحاولة تلقائياً** (`retryable=False`) لأن `needs_human` يحتاج إنساناً |
| `ArenaAgentAdapter` | `backend/app/providers/adapters/arena_agent.py` (341 سطر) | وضع "agent": أوامر الجلسة عبر `command()`, `wait_for_state()`, `new_session()`, `select_repo()`, `submit()`, `keep_working()`, `stop()`, `read_last_reply()`, `selector_test()`, `run_until_quiet()`, `create_pr()`, `close_feedback()`. `ArenaSubmitQueue.slot(profile_id)` يفرض طابور إرسال واحد، و`keep_working_allowed(count)` يطبّق سقف `ARENA_AGENT_MAX_KEEP_WORKING` (0 = بلا سقف)، و`redact_reply()` ينزع الأسرار من الجواب قبل التخزين |
| `ArenaLocalBridgeAdapter` | `backend/app/providers/adapters/arena_bridge.py` (724 سطر) | بروتوكول OpenAI-compatible نحو الجسر: `generate()`, `generate_stream()` (SSE), `get_session()`, `delete_session()`, `health_check()`؛ يمرّر `X-AATM-{Session,Account,Agent,Conversation}-Id` لعزل الجلسات |

التسجيل: `backend/app/providers/adapters/__init__.py` يربط `provider_type` → الصنف: `{"arena_local_bridge": ArenaLocalBridgeAdapter, "arena_agent": ArenaAgentAdapter, "arena_browser": ArenaBrowserAdapter}`. أي أن "موصل Arena" عند AATM = **ثلاثة بروتوكولات مزوّد** فوق جسر واحد، لا موصل واحد.

---

## 6. الجسر المحلي (local bridge)

`bridge/server.py` (978 سطر) — تطبيق FastAPI مستقل، `BRIDGE_VERSION = "2.4.0"`.

| المسار | الحماية | الدور |
| --- | --- | --- |
| `GET /health` | **Bearer** (مُتحقَّق: 200 مع رمز، 401 بدونه) | `status, version, mode (upstream_proxy|diagnostic_only), auth_required, streaming_supported, models, active_sessions, connector_profiles, uptime_seconds` |
| `POST /v1/chat/completions` | Bearer | متوافق OpenAI؛ `model == "arena_browser"` يذهب إلى `hub.dispatch()`، وإلا فهو وضع تشخيصي/تمرير إلى `ARENA_BRIDGE_UPSTREAM_URL` |
| `GET /v1/sessions` · `GET/DELETE /v1/sessions/{id}` | Bearer | ملخّصات/تفاصيل/حذف جلسات معزولة بحساب (`X-AATM-Account-Id`) |
| `WS /v1/connector` | رمز لكل ملف (رسالة `hello`) | النقل بين السكربت والجسر |
| `PUT/DELETE /v1/connector/profiles/{id}`, `POST …/reset`, `POST …/command`, `GET …/profiles[/{id}]` | Bearer (`ARENA_BRIDGE_TOKEN`) | إدارة من الخلفية فقط |
| `GET /mock-arena/` · `GET /mock-arena/agent/` | عام (صفحات محلية ثابتة) | صفحة Arena وهمية للاختبار الشامل بلا شبكة |

خصائص أمنية بُنيت في الجسر (**متحقَّقة بالتنفيذ**): `_verify_bearer_auth()` يقارن بـ `hmac.compare_digest`؛ إن لم يُضبط `ARENA_BRIDGE_TOKEN` فسطح الإدارة **يفشل مغلقاً** (`503 not_configured`) لا مفتوحاً؛ `_require_admin_bearer()` يرسو على `ARENA_BRIDGE_TOKEN` من البيئة فقط (لا قاعدة بيانات، لا ملف تكوين).

---

## 7. تنفيذ الـ userscript (لا إضافة متصفح)

- **userscript في Tampermonkey، لا WebExtension.** لا يوجد `manifest.json` ولا حزمة إضافة في المستودع؛ الإضافة الوحيدة المطلوبة هي Tampermonkey نفسها (توثيق `docs/SETUP_AR.md` §3).
- **التوليد ديناميكي لكل ملف**: `build_userscript(profile, agent, token)` يبني ترويسة `@match` مشتقّة من `match_patterns()` (أي من `ARENA_ALLOWED_ORIGINS` + `ARENA_MOCK_URL` فقط) ويحقن `__AATM_CONFIG__ = {profileId, token, bridge, version}`.
- **حجم ومنع الصلاحيات**: جسم السكربت ~**967 سطر JS**. قياس فعلي على نص الجسم: `@grant none`، ولا وجود لـ `document.cookie` (0)، `localStorage` (0)، `sessionStorage` (0)، `GM_`/`GM.` (0)، `XMLHttpRequest` (0)، `webdriver` (0)، `eval(` (0)، `new Function` (0). القناة الوحيدة: `new WebSocket(CFG.bridge)`.
- **تدقيق قبل التسليم**: `_issue_userscript()` في `api/routes/arena.py` ينادي `validate_userscript_policy(script, patterns)` من `browser/engines.py`، وإن فشل يُرجع HTTP 500 `policy_violation` بدل تسليم سكربت غير مطابق. السياسة تحجب: مراجع CAPTCHA/حلّ التحديات (`2captcha`, `anticaptcha`, `capsolver`, `deathbycaptcha`)، التخفّي (`navigator.webdriver`, `puppeteer-stealth`, `cf_clearance`, `bypass bot/waf`)، الوصول للكوكيز (`document.cookie`, `cookiestore`, `gm_cookie`)، سحب رموز من التخزين، `@grant` محظور (`gm_cookie`/`unsafeWindow`/`GM_xmlhttpRequest`)، `eval`/`new Function`، واعتراض الشبكة.
- **تسليم لمرة واحدة**: الرمز يظهر مرة واحدة في الاستجابة (`token_shown_once: True`)؛ النسخة المحفوظة في جدول `userscripts` **منزوعة الرمز** و`is_enabled=False` و`audit_status="connector_generated"` ولا تُنفَّذ أبداً. بديل: `install_links.py::InstallLinkStore.create/consume` — رابط صالح 600 ثانية، يُستهلك مرة واحدة، ويُخزَّن SHA-256 فقط، وينتهي بإنهاء العملية (تصميم مقصود).
- **حقن برمجي ممنوع**: `BrowserManager.run_userscript()` يرفع 501 نصّاً: «Userscripts are storage only and are not injected or executed.»
- **الإسناد**: جسم السكربت يبدأ بتعليق إسناد لمشروع MIT (`arena-auto-continue`)، مُوثَّق في `THIRD_PARTY_NOTICES.md` مع بيان ما لم يُنقل (لوحة التحكم على الصفحة، مؤقّتات ترسل وحدها، تأخيرات «شبيهة بالبشر»، حيل keep-alive الصوتية، تخزين المتصفح).

---

## 8. إدارة ملفات تعريف المتصفح

| الجانب | التنفيذ | المسار |
| --- | --- | --- |
| ملف Chrome مستقل لكل موظف | `launch_persistent_context(user_data_dir=str(pdir), …)` حيث `pdir = profile.profile_dir` | `browser/manager.py::_launch_playwright_context` (سطر ~293–350) |
| بيانات الملف في قاعدة البيانات | `BrowserProfile` (`profile_dir`, `mode`, `current_url`, `page_title`, `connector_token_hash`, `connector_token_rotated_at`, `connector_status`, `needs_human_reason`, `arena_mode`) | `backend/app/models/platform.py` + ترحيل `a6b7c8d9e0f1_add_browser_profile_connector_fields.py` |
| قفل ملف على القرص | `.aatm.lock` داخل مجلّد الملف + `get_lock_status()`, `_acquire_file_lock()`, `_release_file_lock()`, `_is_pid_alive()` | `browser/manager.py` سطور ~175–277 |
| منع تشغيل نسختين | قفل + PID حيّ → 409 عند المحاولة الثانية | `launch_profile()` |
| إدارة من الواجهة | `GET /api/v1/arena/profiles` (Browser Wall) + `api/routes/platform_browsers.py` | |
| فتح الملف لتسجيل الدخول | `POST /api/v1/arena/profiles/{id}/open-for-sign-in` → `browser_manager.launch_profile(..., mode="visible", url="https://<arena>/")` | `api/routes/arena.py` |
| تحميل إضافة Tampermonkey | `ignore_default_args=["--disable-extensions"]` مقصود كي تُحمَّل Tampermonkey في الملف | `_launch_playwright_context` |
| منع SSRF عند الملاحة | `ctx.route("**/*", self._guard_browser_request)` + `validate_public_navigation_url()` | `browser/manager.py`, `browser/safety.py` |
| تسمية النافذة/الملف | `write_chrome_profile_name(pdir, profile.name)` + `document.title` | `browser/manager.py` |
| لقطة حالة | `has_png_snapshot()`, `capture_snapshot()`, `GET /api/v1/browsers/{id}/snapshot` | |

هذا هو **الجزء الأنضج هندسياً** في AATM من منظور NEXUS: عزل ملف لكل هوية، قفل ملف، منع ملاحة خاصة، ولا قراءة لكوكيز الملف.

---

## 9. نقل الرسائل (transport)

### 9.1 السكربت ↔ الجسر: WebSocket JSON

`ws(s)://127.0.0.1:4100/v1/connector` — رسائل نصية JSON فقط، أربعة أنواع صادرة من الجسر:

| النوع | الاتجاه | الحقول |
| --- | --- | --- |
| `hello` | السكربت → الجسر | `profile_id`, `token`, `page_origin`, `script_version` (مهلة 10 ثوانٍ = `HELLO_TIMEOUT_SECONDS`) |
| `config` | الجسر → السكربت | `dom`, `stop_selectors`, `stop_phrases`, `offline_selectors`, `offline_phrases`, `commands`, `reply_timeout_seconds`, `status`, `mode` |
| `prompt` / `command` | الجسر → السكربت | `request_id`, `prompt` \| (`command`, `args`) |
| `status` / `state` / `event` / `result` / `answer` / `error` | السكربت → الجسر | `request_id`, `ok`, `data`, `code`, `message`, `kind`, `detail` |
| `resumed` | الجسر → السكربت | بعد `reset()` لإعادة المراقبة |

قيود مثبتة: `MAX_PROMPT_CHARS = 120_000`، `MAX_ANSWER_CHARS = 200_000`، `MAX_EVENTS = 50`، اتساع رسالة الخطأ 300 حرف، وأكواد إغلاق محدّدة: `4400` رسالة تالفة/انتهاء مهلة الترحيب، `4401` فشل مصادقة/أصل، `4404` ملف غير مسجّل بعد، `4409` استُبدل باتصال أحدث، `4410` أُلغي التسجيل.

### 9.2 الخلفية ↔ الجسر: HTTP/JSON

`PUT /v1/connector/profiles/{id}` (تسجيل/إعادة تسجيل)، `GET …/profiles` (لقطة حالة)، `POST …/command` (تنفيذ أمر)، `POST …/reset` (استئناف بشري)، `DELETE …/profiles/{id}` (إلغاء)، و`POST /v1/chat/completions` بوضع `arena_browser` (رسالة/جواب OpenAI-style مع `choices[].message.content`).

### 9.3 البث (streaming)

- `POST /v1/chat/completions` في وضع `arena_browser` مع `"stream": true` يعيد **SSE** لكنه **قطعة واحدة + `[DONE]`** لأن الصفحة لا تُنتج تدفّقاً حقيقياً — أي «بث شكلي» لا بث حرف بحرف.
- `ArenaLocalBridgeAdapter.generate_stream()` هو المسار الحقيقي للبث عند وجود مزوّد upstream متوافق OpenAI.

هذا التمييز مهم: **لا يجوز وصف وضع المتصفح بأنه streaming**.

---

## 10. تقرير حالة الاتصال

حالة الملف تعيش في `ProfileState` وتُصدَّر في ثلاثة أماكن:

1. **`ProfileState.summary()`** (الجسر): `status` (`offline|ready|busy|needs_human`)، `health` (`green|yellow|red` — `needs_human` = أحمر، `offline` مع اتصال سابق = أحمر وإلا أصفر)، `connected` (هل الـ WS مفتوح)، `agent_state` (إحدى 8: `ready, generating, idle, keep_working_visible, tool_call_limit, pr_ready, needs_human, offline`)، `agent_state_since`, `agent_state_age_seconds`, `keep_working_visible`, `keep_working_clicks`, `in_flight`, `last_seen_seconds_ago`, `last_error`, `recent_events`, `selector_report`, `script_version`, `origin`.
2. **`GET /api/v1/arena/connector/status`** (الخلفية): يعيد `arena_gate()` + `bridge` + `status_label ∈ {enabled, mock, disabled}` + سطر صريح `run_userscript: "disabled (501)…"`.
3. **`GET /api/v1/arena/profiles`** (Browser Wall) و`GET /api/v1/arena/agent/overview`: بطاقة لكل موظف فيها `connector_status`, `connector`, `needs_human_reason`, `token_issued`, `arena_mode`, `health` (`_health()` يدمج حالة قاعدة البيانات مع حالة الجسر). الواجهة: `frontend/src/views/ArenaViews.tsx` — شارات `ready/idle/generating/keep_working_visible/tool_call_limit/pr_ready/needs_human/offline` و«بانتظار إنسان» + زر «استئناف».

نقل الحالة إلى قاعدة البيانات: `arena_sessions.apply_bridge_state(session, summary)` يضبط `page_state` و`last_state_change_at` ويضيف حدثاً عند كل تغيير، و`bridge_profile_state()` يجمعها في `sync_session()`.

---

## 11. الإعدادات

### 11.1 الخلفية (`backend/app/core/config.py`)

| المفتاح | الافتراضي | المعنى |
| --- | --- | --- |
| `ARENA_CONNECTOR_ENABLED` | `false` | البوابة الرئيسية لكل استخدام حقيقي لـ Arena |
| `ARENA_ALLOWED_ORIGINS` | `https://arena.ai` | أصول `@match` المسموحة (كائمة مفصولة بفواصل) |
| `ARENA_BRIDGE_URL` | `http://127.0.0.1:4100` | عنوان الجسر |
| `ARENA_BRIDGE_TIMEOUT` | `600` | مهلة عامة |
| `ARENA_BRIDGE_MAX_CONCURRENCY` | `1` | تزامن لكل ملف |
| `ARENA_MOCK_URL` | `""` | صفحة وهمية (loopback فقط) |
| `ARENA_REPLY_TIMEOUT_SECONDS` | `600` | مهلة الجواب |
| `ARENA_AGENT_NEW_SESSION_URL` | `""` | عنوان جلسة جديدة (افتراضياً `{origin}/agent`) |
| `ARENA_AGENT_MAX_KEEP_WORKING` | `0` | سقف متابعات «Keep working» (0 = بلا سقف) |
| `ARENA_DOM_SELECTORS` | `""` | JSON محددات DOM تُمرَّر للسكربت كبيانات |
| `ARENA_PR_STATE_POLL_SECONDS` | `300` | دورية فحص حالة طلب الدمج |
| `ARENA_MANAGER_*`, `AATM_MANAGER_PROVIDER` | — | إعدادات مدير Arena |
| `BROWSER_PROFILES_DIR`, `BROWSER_EXECUTABLE_PATH` | `data/browser_profiles`, `""` | ملفات المتصفح والمحرك |
| `AGENT_MAX_PARALLEL` | مشتق | `max(DEFAULT_ACTIVE_WORKERS, ARENA_BRIDGE_MAX_CONCURRENCY)` |

### 11.2 الجسر (بيئة العملية، `bridge/README.md`)

`ARENA_BRIDGE_HOST` (`127.0.0.1`)، `ARENA_BRIDGE_PORT` (`4100`)، `ARENA_BRIDGE_TOKEN` (بلا افتراضي)، `ARENA_BRIDGE_REQUIRE_AUTH` (`false` — يُنصح `true`)، `ARENA_BRIDGE_MAX_HISTORY` (`40`)، `AATM_BRIDGE_STATE_FILE`، `AATM_BRIDGE_SESSION_TTL_SECONDS`، `ARENA_BRIDGE_UPSTREAM_URL`، `ARENA_BRIDGE_UPSTREAM_API_KEY`، `ARENA_CONNECTOR_ENABLED` (**في بيئة الجسر أيضاً**)، `ARENA_CONNECTOR_STATE_FILE`، `ARENA_REPLY_TIMEOUT_SECONDS`.

**ملاحظة مهمة:** البوابة مزدوجة القفل — `real_enabled` يُسجَّل من الخلفية، **و**الجسر يشترط `ARENA_CONNECTOR_ENABLED=true` في بيئته هو (`real_arena_allowed_by_bridge()`). متحقَّق بالتنفيذ: محاولة تسجيل أصل حقيقي بلا المتغيّر → `not_enabled` / 403.

---

## 12. معالجة الأخطاء

| المصدر | الصنف/الآلية | الأكواد |
| --- | --- | --- |
| الجسر | `ConnectorError(code, message, http_status)` → `_http_error()` | `invalid_origin`(422), `not_enabled`(403), `invalid_token_hash`(422), `invalid_new_session_url`(422), `not_registered`(404), `offline`(503), `needs_human`(409), `timeout`(504), `prompt_too_large`(413), `unknown_command`(422), `text_required`(422), `invalid_repo`(422), `script_outdated`(409), `command_failed`(502), `not_configured`(503) |
| الخلفية (بوابة) | `ArenaNotEnabled` → 409 `not_enabled` | `NOT_ENABLED_MESSAGE` موحّدة |
| محوّل الوكيل | `ArenaAgentError(code, message)` | `bridge_error`, `needs_human`, `timeout`, `repo_not_selected`, `send_failed`, `stop_failed` |
| محوّل المتصفح | `_fail(..., code, ...)` → `ProviderResponse(success=False, retryable=False)` | `not_enabled`, `profile_required`, `dry_run`, `bridge_unreachable`, `http_*`, `needs_human` |
| السكربت | `event{kind:"send_failed"|"error"}` + `result{ok:false, code, message}` | `composer_not_found`, `page_hidden` … |
| الوكيل | `last_error` على `ProfileState` + `error_message` على `ArenaSession` | يظهر في بطاقة الواجهة |

ثلاث ممارسات جيدة تستحق النقل:
1. **`retryable=False`** على أخطاء الموصل: إعادة المحاولة على `needs_human` تعني تجاوز تحقّق بشري — فمنعها مقصود.
2. **تمييز `offline` عن `needs_human`** عند الانقطاع: `handle_socket()` في `finally` يضبط `offline` ولا يلمس `needs_human` إن كان قائماً (التحقّق البشري يجب أن يبقى بعد إعادة الاتصال).
3. **`_fail_pending(..., include_commands=False)`** عند `needs_human`: الرسائل غير المُسلَّمة تُفشل فوراً، لكن أمر وكيل أُرسل قبل ظهور التحقق **ينتظر نتيجته** لأنه ربما نُفِّذ فعلاً.

---

## 13. نموذج الأمان

### 13.1 طبقات المصادقة والتفويض

| الطبقة | الآلية | الملف |
| --- | --- | --- |
| مستخدم ← API | JWT + `get_current_user` + `require_role("admin"/"operator")` على كل مسار كتابة | `api/routes/arena.py`, `api/deps.py` |
| خلفية ← جسر | `Authorization: Bearer $ARENA_BRIDGE_TOKEN` + `hmac.compare_digest` + فشل مغلق `503` إن لم يُضبط | `bridge/connector.py::_require_admin_bearer`, `bridge/server.py::_verify_bearer_auth` |
| سكربت ← جسر | رمز لكل ملف، **SHA-256 فقط مخزّن** + التحقق من أصلين: `page_origin ∈ allowed_origins` و`Origin` الترويسة == `page_origin` | `_authenticate()`, `mint_token()` |
| جسر ← خدمة خارجية | `ARENA_BRIDGE_UPSTREAM_URL` فقط (OpenAI-compatible رسمي/محلي) | `bridge/server.py` |
| ربط الاعتماد | `credential_ref` مسموح فقط بـ `env:*_API_KEY` أو allowlist؛ `ARENA_BRIDGE_TOKEN` مربوط بمزوّد `arena_local_bridge` ويُرسَل إلى loopback/`ARENA_BRIDGE_URL` فقط | `providers/credential_policy.py`, `docs/SECURITY.md` |

### 13.2 ما لا يفعله AATM (مثبت بالشيفرة والتوثيق)

- **لا يجمع كلمات المرور ولا يسجّل الدخول**: `docs/SETUP_AR.md` §4 نصّاً: «كل شخص يسجّل الدخول بحسابه الخاص بنفسه … AATM لا يطلب كلمات مرور ولا يسجّل الدخول ولا يقبل الشروط ولا يحل أي تحقق بشري نيابة عن أحد».
- **لا يقرأ كوكيز/تخزين/رموز**: `arena_connector.py` توثيق الوحدة + قياس على جسم السكربت (لا `document.cookie` ولا `localStorage`)، و`validate_userscript_policy` تحجب ذلك بنيوياً.
- **لا يحلّ CAPTCHA ولا يتجاوز anti-bot**: قائمة `DEFAULT_STOP_SELECTORS` (11 محدّداً: `iframe[src*='captcha']`, `challenges.cloudflare.com`, `turnstile`, `hcaptcha`, `recaptcha`, …) و`DEFAULT_STOP_PHRASES` (14 عبارة: «verify you are human», «unusual traffic», «rate limit», «accept the terms», «sign in to continue», …) **للإيقاف لا للتجاوز**.
- **لا يخفي الطابع الآلي**: لا `navigator.webdriver` spoofing، ولا تأخيرات «شبيهة بالبشر» (موثّق صراحةً في `THIRD_PARTY_NOTICES.md` كخصائص **لم** تُنقل).
- **لا تجميع/تدوير حسابات**: ملف مستقل لكل موظف، ولا Account Pooling في الشيفرة.
- **لا سجلات للأسرار**: تعليق `bridge/connector.py`: «prompts, answers and tokens are never logged (only ids, lengths and statuses)»؛ و`security.py`/`agent_protocol.py` تنزع الأسرار قبل الإرجاع (`redact_secrets`, `redact_extracted_text`).
- **تدقيق**: `AuditLog` لكل عملية حسّاسة (`arena.userscript_generated`, `arena.userscript_rotated`, `arena.mode_changed`, `arena.open_for_sign_in`, `arena.install_link_created`, `arena.human_resolved`).

### 13.3 تناقض توثيقي يستحق التحذير

`docs/SECURITY.md` §8 يحتوي السطر: «One in-flight request per profile, **a minimum delay between requests and a daily cap**, which survives token rotation». **هذا لا يطابق الشيفرة**: `bridge/connector.py` ينصّ في ترويسته على «there are no request intervals, daily caps, profile-count limits or other usage quotas»، و`ProfileState` لا يحمل أي عدّاد تأخير أو سقف يومي. الخلفية تعتمد على قيد «طلب واحد متزامن لكل ملف» فقط. **الاعتماد على الوثيقة هنا خطأ؛ الشيفرة هي الحجّة.** هذه فجوة توثيقية في AATM يجب ألا تُنقل إلى NEXUS.

### 13.4 ثغرة تصميمية أُوصي بإصلاحها في NEXUS

`needs_human` عند AATM يحمل دلالتين مختلفتين خطيراً خلطهما:
- **جدار تسجيل دخول** («sign in to continue»، «log in to continue») — الحلّ المشروع: إنسان يسجّل الدخول بنفسه.
- **تحقّق بشري/CAPTCHA/حدّ معدل/شروط** — الحلّ: **توقّف، ولا مساعدة إطلاقاً**.

خلطهما في حالة واحدة يجعل مفهوم «استئناف» غامضاً وقد يدفع مشغّلاً لاستئناف ملفّ فيه CAPTCHA. تصميم NEXUS يفصلهما (§17: `awaiting_auth` مقابل `blocked_human_check`). كما أن `reset()` يسمح بالإفراج عن الحالة من مسار `admin/operator` دون تمييز السبب، و`READ_ONLY_COMMANDS + SAFE_STOP_COMMANDS` تعمل وهي موقوفة (مقبول، لكن يجب توثيقه صراحةً).

### 13.5 حدود التصميم الأمني في AATM (بلا ادّعاء)

- المرجع «ARENA-TEMP-2026-054» في `docs/SETUP_AR.md` §0 هو **موافقة مشغّل داخلية** (حدّ 4 ملفات، «تطوير واختبار داخلي فقط») وليست مستنداً من خدمة Arena. **غير متحقق** أن أي جهة خارجية أقرّت هذا الاستخدام.
- AATM لا يوثّق أن الاستخدام عبر المتصفح **مدعوم رسمياً** من Arena. لكنه أيضاً لا ينصّ على العكس في مكان واحد بارز؛ التوثيق يصف الآلية بحذر («human signs in manually») دون جملة نفي صريحة. NEXUS يجب أن يحمل جملة النفي صريحة (§18).

---

## 14. هل موصل Arena قابل لإعادة الاستخدام أو التكييف داخل NEXUS OSINT؟

**الحكم المفصّل بحسب المكوّن:**

| المكوّن | الحكم | السبب |
| --- | --- | --- |
| بروتوكول WS (`hello`/`config`/`command`/`result`/`status`) | ✅ **قابل لإعادة الاستخدام كمواصفة** (إعادة تنفيذ) | بسيط، موثّق ضمناً، قابل للاختبار بسكربت وهمي؛ لا يعتمد على AATM |
| نموذج `ProfileState` + `summary()` | ✅ **قابل للتكييف** (نمط) | حقول الحالة كافية ومحدّدة؛ ناقصها تفريق §17 |
| `token_sha256` لكل ملف + التحقق من أصلين | ✅ **قابل لإعادة الاستخدام كتصميم** | صحيح ومختبَر بالتنفيذ عندي (28/28) |
| بوابة `arena_gate()` ثنائية القفل (خلفية + جسر) | ✅ **قابل لإعادة الاستخدام كتصميم** | يمنع تفعيل «حقيقي» من طبقة واحدة |
| قائمة أوامر مغلقة (9) + `_validate_command()` | ✅ **قابل لإعادة الاستخدام** | منع واضح لأي أمر عشوائي من الـ LLM |
| `validate_userscript_policy()` + تعبيراته | 🟡 **مفيد كمرجع، يُعاد كتابته** | تعبيراته جيدة لكن مبنية حول Tampermonkey `@grant`؛ NEXUS يحتاج سياسة أوسع (منع أي `eval`, `Function`, cookie, storage, network hooks) |
| `build_userscript()` + `USERSCRIPT_BODY` (967 سطراً) | ⛔ **لا يُنسخ** | (1) مُشتق من مشروع MIT خارجي فيلزم إشعار وإعادة تقييم؛ (2) بلا ترخيص AATM؛ (3) محشوّ بمنطق DOM خاص بـ Arena |
| `ArenaBrowserAdapter` / `ArenaAgentAdapter` / `ArenaLocalBridgeAdapter` | 🔴 **غير قابل للاستخدام مباشرة** | يعتمد على `BaseProviderAdapter` و`ProviderRequest/Response` و`get_settings()` ونماذج SQLAlchemy |
| `browser/manager.py` (Playwright/Chrome) | 🟡 **نمط مفيد، لا كود** | تشغيل Chrome بالمتصفح يتعارض مع نموذج NEXUS (نحن لا نُشغّل متصفحاً آلياً) |
| `bridge/server.py` (FastAPI loopback + Bearer + fail-closed) | ✅ **قابل لإعادة الاستخدام كتصميم** وإعادة تنفيذ مستقل | بنية نظيفة قابلة للتكرار في ~300 سطر |
| مستودع الاختبارات (`backend/tests`, 91 ملفاً) | ✅ **مرجع لسيناريوهات** | أسماء سيناريوهات مفيدة: `test_arena_page_states`, `test_arena_disconnect_dispatch`, `test_arena_recovery`, `test_arena_bridge_restart`, `test_r2_arena_userscript` |

**الخلاصة:** إعادة الاستخدام **معمارية/بروتوكولية** نعم؛ **نسخ كود** لا — الحائل الترخيصي (لا `LICENSE`) وحده يمنع النسخ، والحائل الهندسي (تشابك مع نموذج بيانات AATM) يجعل النسخ مكلفاً حتى لو وُجد ترخيص.

**بديل ثالث (المعتمد هنا):** مواصفة بروتوكول مكتوبة من الصفر في §19، وتنفيذ مستقل داخل NEXUS، مع الاستفادة من الدروس الأمنية لا من الشيفرة.

---

## 15. ما تم التحقق منه بالتنفيذ (وليس بالقراءة)

شُغِّل `tests/manual/probe_aatm_connector.py` (مرفق في هذا المستودع، **لا** يُجمَع ضمن `unittest discover`) ضد نسخة AATM عند `1da237f` في بيئة معزولة. النتيجة: **28/28 ناجح**.

| ما تحقّق فعلياً | النتيجة المقيسة |
| --- | --- |
| تسجيل ملف على أصل loopback | ناجح |
| أصل حقيقي + `real_enabled=True` بلا `ARENA_CONNECTOR_ENABLED` | رُفض: `not_enabled` / 403 |
| أصل حقيقي بلا `real_enabled` | رُفض: `not_enabled` / 403 |
| رمز ملف خاطئ في `hello` | أُغلق الاتصال بالكود `4401` |
| رمز صحيح | وصل إطار `config` مع قائمة الأوامر التسعة، **ولا يحتوي الرمز** |
| `page_origin` غير مسموح | أُغلق `4401` |
| `status: needs_human` | `status="needs_human"`، `health()="red"` |
| `submit` أثناء `needs_human` | رُفض `needs_human` / 409 |
| `read_last_reply` أثناء `needs_human` | مرّ (أمر قراءة) |
| `reset()` | أعاد الحالة إلى `ready` |
| أوامر `eval_js` / `click_captcha` / `solve` / `read_cookies` | رُفضت `unknown_command` / 422 |
| `repo="../../etc/passwd"` | رُفض `invalid_repo` / 422 |
| نص 200,001 حرف | رُفض `prompt_too_large` / 413 |
| `new_session` لعنوان خارج الأصول | رُفض `invalid_new_session_url` / 422 |
| `GET /health` برمز / بدونه | 200 / **401** |
| `GET /v1/connector/profiles` برمز خاطئ / صحيح | 401 / 200 |
| `PUT /v1/connector/profiles/{id}` بتجزئة غير صالحة | 422 |
| تسجيل أصل حقيقي عبر HTTP بلا بوابة | 403 `not_enabled` |
| `ARENA_BRIDGE_TOKEN` غير مضبوط | 503 (فشل مغلق) |
| جسم السكربت المُولَّد: عدّ الأنماط المحظورة | `document.cookie`=0، `localStorage`=0، `sessionStorage`=0، `GM_`/`GM.`=0، `XMLHttpRequest`=0، `webdriver`=0، `eval(`=0، `new Function`=0 |

**ما لم يُختبر (غير متحقق)**: التشغيل الكامل لـ AATM (خادم + DB + Chrome + Tampermonkey)، أي تفاعل مع `arena.ai` الحقيقي، `backend/tests` (91 ملفاً — تحتاج `backend/requirements.txt` كاملاً وقاعدة بيانات)، والواجهة. كما **لم** يُختبر أي تكامل AATM↔NEXUS لأنه **غير موجود**.

---

## 16. تدفق الاستخدام اليدوي للمصادقة (كما هو في AATM، بخطوات مرقّمة)

هذا هو التدفق الذي يُقترح **تكييفه لا نسخه** في NEXUS. كل خطوة بمصدرها:

1. **تفعيل البوابة (مشغّل):** `ARENA_CONNECTOR_ENABLED=true` + `ARENA_ALLOWED_ORIGINS` في `.env` ← `arena_gate()["mode"] == "real"`. بدون ذلك كل مسار حقيقي يعيد 409 `not_enabled`.
2. **ملف متصفح لكل هوية:** ملف Chrome مستقل (`profile.profile_dir`, `--user-data-dir`). لا مشاركة تسجيل دخول بين ملفين.
3. **فتح الملف لتسجيل الدخول (إنسان):** `POST /api/v1/arena/profiles/{id}/open-for-sign-in` → `launch_profile(..., mode="visible", url="https://<arena-origin>/")`. **الإنسان** يكتب بريده/كلمته، ينهي 2FA، يقبل الشروط، ويربط GitHub إن لزم. AATM لا يرى أي من ذلك.
4. **توليد السكربت ورمزه (مسؤول):** `POST /api/v1/arena/profiles/{id}/userscript` → `mint_token()` + `build_userscript()` + `validate_userscript_policy()` + `register_profile_with_bridge()` (أي `PUT /v1/connector/profiles/{id}` إلى الجسر) + `AuditLog`. الرمز يظهر **مرة واحدة**؛ المخزَّن SHA-256 فقط. بديل: `POST …/install-link` (رابط لمرة واحدة، 600 ثانية) ثم `GET /api/v1/arena/install/{token}` (بلا تسجيل دخول — الرابط نفسه هو الاعتماد).
5. **تثبيت السكربت (إنسان):** Tampermonkey → «Allow User Scripts» → لصق/تثبيت السكربت → **منح إذن «الوصول إلى الشبكة المحلية»** للصفحة (بدونه يُحجب `ws://127.0.0.1:4100` بصمت) → إعادة تحميل الصفحة.
6. **ارتباط تلقائي (السكربت ↔ الجسر):** `hello{profile_id, token, page_origin, script_version}` → الجسر يتحقق من SHA-256 + الأصلين → يرسل `config`.
7. **تأكيد الجاهزية (مسؤول):** البطاقة تصبح «متصل»؛ `selector_test` (قراءة فقط) يتحقق من `composer`, `send`, `new_session`, `human_check: none`, `offline: none`, `ok: true`.
8. **التشغيل:** `claim_session()` → `new_session` → `submit` (مع `repo`) → مراقبة `agent_state` → `keep_working` عند الحاجة → `read_last_reply` → `create_pr`.
9. **عند التحقق البشري:** الملف يتوقف (`needs_human`)، المهمة تُحجب، إشعار حرج. **الإنسان** يحلّ التحقق في المتصفح ثم `POST /api/v1/arena/profiles/{id}/resume` → `reset()` على الجسر + إعادة جدولة مهام الجلسة الحالية فقط (`requeued_tasks` / `skipped_tasks`).

**ممنوع في كل خطوة:** لا تخزين لكلمة مرور، لا أتمتة لتسجيل الدخول، لا قراءة كوكيز، لا تمرير جلسة بين ملفين، لا حلّ لأي تحقق.

---

## 17. حالات الحالة المطلوبة في NEXUS (خمس حالات + حالتان داخليتان)

المطلوب صراحةً: **متصل، غير متصل، بانتظار المصادقة، الموصل غير متاح، خطأ**. التعريفات التالية تفصل ما خلطه AATM:

| الحالة | الرمز المقترح | معناها الدقيق | شروط الدخول | ما يُسمح | ما يُمنع |
| --- | --- | --- | --- | --- | --- |
| **متصل** | `connected` | الموصل والجسر والملف جاهزون لاستقبال مهمة | مصادقة ناجحة + `hello` مقبول + لا تحقق بشري معلّق + `health="green"` | إرسال مهمة واحدة، أوامر القراءة | إرسال متزامن ثانٍ |
| **غير متصل** | `disconnected` | كان متصلاً ثم انقطع (تبويب مغلق/شبكة/إعادة تحميل) | فقدان WS بعد اتصال ناجح | انتظار إعادة الاتصال بتراجع أسّي | اعتبار المهمة فاشلة فوراً؛ إعادة المحاولة العمياء بلا حدّ |
| **بانتظار المصادقة** | `awaiting_auth` | جدار تسجيل دخول أو جلسة منتهية: **إنسان يجب أن يسجّل الدخول بنفسه** | رصد مؤشرات جدار دخول فقط | إيقاف المهمة، إشعار، فتح الملف للإنسان | أي محاولة تعبئة اعتماد، أي إعادة توجيه تلقائي، أي «متابعة» آلية |
| **الموصل غير متاح** | `connector_unavailable` | الجسر لا يستجيب / الوحدة معطّلة / الملف غير مسجّل / الرمز غير صالح | فشل اتصال بالجسر، أو `not_enabled`/`not_registered`/`script_outdated` | إعادة محاولة محدودة + تعطيل التوجيه إلى هذا الموصِل | التعامل معه كـ«غير متصل» عادي (يحتاج تدخل مشغّل غالباً) |
| **خطأ** | `error` | فشل تنفيذ محدد (اختيار عنصر، إرسال، مهلة، تجاوز حد) | أكواد §12 | تسجيل الكود، إعادة محاولة محدودة إن كان قابلاً، تصعيد | إعادة المحاولة على `blocked_human_check` |
| *(داخلي)* | `busy` | طلب/أمر جارٍ الآن | بين الإرسال والنتيجة | لا شيء آخر على نفس الملف | إرسال ثانٍ |
| *(داخلي، مرفوض)* | `blocked_human_check` | CAPTCHA/تحقق/شروط/حدّ معدل: **توقف نهائي بلا مساعدة** | رصد محدّد/عبارة | إيقاف، إشعار، تدخل بشري مدرَّب | **أي** محاولة تجاوز أو مساعدة أو إعادة محاولة |

جدول الانتقالات (مختصر): `connector_unavailable → disconnected → awaiting_auth → connected → busy → connected`؛ وأي حالة `→ blocked_human_check` توقف كل شيء حتى تدخل بشري صريح مع سبب مسجَّل.

مقابلها في AATM: `connected≈ready/busy`، `disconnected≈offline`، `awaiting_auth` **مدموج** في `needs_human`، `connector_unavailable≈bridge_unreachable/not_enabled/no_token`، `error≈last_error/error_message`. الفصل أعلاه هو الإضافة الحقيقية المطلوبة في NEXUS.

---

## 18. القيود الإلزامية (نصّ صريح ملزم)

القيود التالية **ملزمة لأي عمل مستقبلي على وحدة `NEXUS Arena Bridge` أو محوّل `AATM Integration Adapter`**، وتُنقل حرفياً إلى أي وثيقة تنفيذ أو مراجعة أو PR:

1. **لا تجاوز مصادقة.** لا تُعبّأ كلمة مرور، ولا يُنقر زر دخول، ولا تُستأنف جلسة منتهية آلياً، ولا تُمرَّر جلسة بين ملفات أو هويات. المصادقة يقوم بها إنسان في متصفحه.
2. **لا تجاوز CAPTCHA.** لا حلّ، ولا تمرير لخدمة خارجية، ولا تخفّي، ولا تعطيل لكشف الأتمتة، ولا `navigator.webdriver` spoofing. عند رؤية أي تحدٍّ: **توقّف وأبلغ**.
3. **لا استخراج كوكيز المتصفح.** لا `document.cookie`، ولا `Cookie` header، ولا `cookies` في أي API، ولا قراءة ملف تعريف Chrome على القرص.
4. **لا تصدير رموز مصادقة.** لا رمز جلسة، ولا JWT، ولا مفتاح API، ولا رمز موصل يخرج من نطاق الملف صاحبه (لا إلى سجل، ولا إلى نتيجة مهمة، ولا إلى AATM/جهة خارجية). يُخزَّن SHA-256 فقط.
5. **لا تدوير حسابات.** لا تجميع حسابات، ولا تبديل هوية عند الحدود أو الحجب، ولا «حساب احتياطي» يعمل مكان المحجوب.
6. **لا تطبيع أي نشاط محظور.** لا تُغلَّف مخالفة الشروط داخل «ميزة» ولا تُسمّى «أتمتة مساعدة» ولا تُخفى في خيار إعداد؛ ما هو محظور يبقى محظوراً ويرفضه الكود بخطأ صريح.
7. **عدم الادعاء بأن الوصول عبر المتصفح مدعوم رسمياً إن لم توثّقه الخدمة.** في كل وثيقة وواجهة وسجل: يُذكر أن هذا استخدام عبر واجهة المستخدم بمبادرة المشغّل، **غير مصرّح به رسمياً** ما لم يوجد مستند من الخدمة يقرّه — ولا يوجد في هذه المراجعة أي مستند كهذا (`غير متحقق` على الإطلاق).

**قيود تشغيلية مضافة (من دروس AATM):**
8. **البوابة مغلقة افتراضياً** في طبقتين (الوحدة + الجسر)، ولا تُفتح إلا بقرار مشغّل مسجّل.
9. **طلب/أمر واحد في وقت واحد لكل ملف**، ولا تزامن على نفس التبويب.
10. **ربط loopback فقط** للجسر، مع Bearer وفشل مغلق عند غياب الرمز.
11. **لا سجلات لمحتوى الموجّهات أو الأجوبة** — أطوال ومعرّفات وأكواد فقط.
12. **تدقيق لكل تفعيل/تسجيل/استئناف** بسبب وممثل.

---

## 19. تصميم وحدة `NEXUS Arena Bridge` (اختيارية)

> اقتراح تصميم. **غير منفّذ، غير مختبر، وغير موثوق به.** الأسماء أدناه تصف واجهة مقترحة؛ يجب مطابقتها مع بنية NEXUS الفعلية قبل أي تنفيذ.

### 19.1 الغرض والحدود

وحدة **اختيارية**، تُشغَّل كعملية محلية (loopback) منفصلة عن نواة NEXUS، تملك النقل بين سكربت يعمل في متصفح المستخدم وبين NEXUS. النواة (النظام الأساسي لـ NEXUS OSINT) **لا تستوردها ولا تعتمد عليها**؛ تتحدث معها عبر واجهة `ArenaTransport` اختيارية.

```
nexus/
  integrations/arena_bridge/          # optional package, never imported by core
    __init__.py                       # public surface: ArenaTransport, ArenaState, BridgeConfig
    protocol.py                       # message schemas (dataclasses/pydantic), versioned
    states.py                          # the 7 states of §17 + transition table (pure functions)
    policy.py                          # the 7 mandatory constraints as executable guards
    server.py                          # FastAPI loopback app: /health, /v1/connector (WS), admin
    registry.py                        # per-profile registry: token hash, origins, status
    client.py                          # NEXUS-side HTTP client implementing ArenaTransport
    config.py                          # NEXUS_ARENA_* settings (all default-off)
  integrations/aatm_adapter/          # optional adapter (§20)
```

### 19.2 واجهة النواة (الحد الفاصل)

```python
class ArenaTransport(Protocol):           # implemented by arena_bridge.client
    async def health(self) -> dict: ...           # never raises; returns {"state": ArenaState, ...}
    async def list_profiles(self) -> list[dict]: ...
    async def profile_state(self, profile_id: str) -> dict: ...
    async def dispatch(self, profile_id: str, prompt: str, *, timeout: float) -> str: ...
    async def command(self, profile_id: str, name: str, args: dict, *, timeout: float) -> dict: ...
    async def reset(self, profile_id: str, *, reason: str, actor: str) -> dict: ...
```

كل الدوال **لا ترفع استثناءات للشبكة**: تُرجع `{"state": ..., "code": ..., "message": ...}`. هذا مباشرةً من درس AATM (`bridge_call()` تعيد `{"ok": False, ...}` بدل رفع استثناء)، ويحمي نواة NEXUS من انهيار ميزة أساسية بسبب وحدة اختيارية.

### 19.3 الإعدادات (كلها معطّلة افتراضياً)

| المفتاح | الافتراضي | ملاحظة |
| --- | --- | --- |
| `NEXUS_ARENA_BRIDGE_ENABLED` | `false` | بوابة الوحدة |
| `NEXUS_ARENA_BRIDGE_REAL_ENABLED` | `false` | بوابة الاستخدام الحقيقي (لا mock) |
| `NEXUS_ARENA_BRIDGE_HOST` / `PORT` | `127.0.0.1` / `4110` | loopback فقط؛ رفض أي واجهة أخرى |
| `NEXUS_ARENA_BRIDGE_TOKEN` | — | Bearer للجسر؛ غيابه = فشل مغلق |
| `NEXUS_ARENA_ALLOWED_ORIGINS` | `""` | فارغة = الوحدة معطّلة |
| `NEXUS_ARENA_MOCK_ORIGIN` | `""` | loopback فقط (نمط `mock_url()` في AATM) |
| `NEXUS_ARENA_REPLY_TIMEOUT_SECONDS` | `600` | مهلة الجواب |
| `NEXUS_ARENA_MAX_CONCURRENT_PER_PROFILE` | `1` | لا يزيد |
| `NEXUS_ARENA_DISCLOSURE_ACK` | `false` | إقرار المشغّل بأنه قرأ §18؛ شرط للتفعيل الحقيقي |

### 19.4 بروتوكول الرسائل (نسخة `1`)

```jsonc
// script -> bridge (first frame, ≤10 s)
{"type":"hello","v":1,"profile_id":"…","token":"…","page_origin":"https://…","script_version":"1.0.0"}
// bridge -> script
{"type":"config","v":1,"dom":{…},"stop_selectors":[…],"stop_phrases":[…],
 "offline_selectors":[…],"offline_phrases":[…],"commands":[…],"reply_timeout_seconds":600}
// bridge -> script
{"type":"command","request_id":"…","command":"submit","args":{"text":"…"}}
// script -> bridge
{"type":"result","request_id":"…","ok":true,"data":{…}}
{"type":"state","state":"connected|busy|awaiting_auth|blocked_human_check|error","reason":"…"}
{"type":"event","kind":"error","detail":"…"}
```

قواعد النسخة: `v` إلزامي؛ الجسر يرفض إطاراً بلا `v` أو بـ`v` مختلف بالكود `unsupported_version` (بدل الصمت)؛ أطوال النصوص محدّدة مسبقاً؛ `request_id` إلزامي في `result`.

### 19.5 دورة الحالة

`states.py` يحمل دالّة انتقال نقية `next_state(current, event) -> ArenaState` مع **جدول مسموح** (لا انتقالات حرة). مثال قيود إلزامية:
- لا انتقال من `blocked_human_check` إلا بحدث `human_resolved{reason, actor}` مسجّل من واجهة إدارية.
- `awaiting_auth → connected` يتطلب `hello` جديداً بعد إعادة تحميل الصفحة (أي أن إنساناً سجّل الدخول فعلاً)، لا مجرد مرور وقت.
- أي حدث `human_check_seen` من أي حالة → `blocked_human_check` (توقّف مطلق).

### 19.6 ما لا تفعله الوحدة (بنود مرجعية)

لا تُشغّل متصفحاً، لا تُنزّل سكربتاً نيابةً عن المستخدم، لا تحقن `BrowserManager`-شبيهاً، لا تقرأ ملف تعريف المتصفح، لا تخزّن رمزاً صريحاً، ولا تُفعّل نفسها. **تُسلّم السكربت للمستخدم ليقرأه ويثبّته بنفسه** في مدير سكربتات (Tampermonkey أو مثيله).

---

## 20. تصميم محوّل `AATM Integration Adapter` (اختياري)

### 20.1 المبدأ: اتجاه واحد للاعتماد

```
NEXUS core  ──uses──►  AATM Integration Adapter  ──HTTP──►  AATM API
     ▲                        │
     └── never imports ───────┘   (adapter depends on core, never the reverse)
```

النواة تعرّف عقداً اختيارياً (`TaskExchange` protocol). المحوّل ينفّذه. إن غاب المحوّل أو غاب AATM، النواة تعمل بكامل وظائفها مع `integration: unavailable`. **لا يظهر اسم AATM في أي وحدة أساسية.**

### 20.2 العقود الأربعة المطلوبة (تفويض المهام، حالة الوكلاء، النتائج، الأخطاء)

| العقد | الاتجاه | الحقول الأساسية |
| --- | --- | --- |
| **تفويض مهمة** `TaskDelegation` | NEXUS → AATM | `delegation_id` (مفتاح تكرار idempotency)، `title`, `objective`, `acceptance_criteria[]`, `constraints[]` (تشمل §18 كنصّ صريح)، `priority`, `deadline`, `repo_hint`, `capabilities[]`, `callback_url` (اختياري)، `requested_by`, `correlation_id` |
| **حالة وكلاء** `AgentStatus` | AATM → NEXUS | `delegation_id`, `agent_ref` (معرّف خارجي مبهم، **لا** بريد ولا اسم حساب)، `state ∈ {connected, disconnected, awaiting_auth, connector_unavailable, error}` **مُطبَّعة إلى §17**، `state_since`, `progress_pct?`, `note?`, `updated_at` |
| **نتيجة** `TaskResult` | AATM → NEXUS | `delegation_id`, `outcome ∈ {done, partial, blocked, failed, rejected_policy}`, `summary`, `artifacts[]` (مسارات/روابط، بلا محتوى اعتماد), `tests_run[]`, `pr_url?`, `finished_at`, `evidence_refs[]` |
| **خطأ** `IntegrationError` | أي اتجاه | `code` من تصنيف مغلق (`auth_failed`, `policy_refused`, `rate_limited`, `timeout`, `unavailable`, `invalid_payload`, `conflict`)، `message`, `retryable: bool`, `retry_after_s?`, `correlation_id` |

### 20.3 تنسيق اختياري (معطّل افتراضياً)

- `capability_announcement` — يعلن AATM ما يستطيع فعله؛ NEXUS يفوّض فقط ما يطابق.
- `lease/claim` — NEXUS يعرض مهمة، AATM يطالب بها بقفل زمني (`lease_seconds`) وإعادة عرضها إن انتهى.
- `cancellation` — إلغاء متفائل مع مهلة سماح، ونتيجة `partial` إن نُفِّذ جزء.
- `heartbeat` — كل 30 ثانية؛ غياب 3 نبضات = `unavailable` (لا `failed`).

كل ما سبق **اختياري ومغلق افتراضياً**، وكل عقد يُفعَّل بمفتاحه.

### 20.4 عزل الفشل والحدود الأمنية للمحوّل

- **زمن المهلات**: اتصال 5 ثوانٍ، قراءة 30 ثانية، إجمالي 60 ثانية؛ `circuit breaker` بعد 3 أخطاء متتالية → `unavailable` لمدة 5 دقائق.
- **إعادة المحاولة**: فقط على `retryable=true` وبتراجع أسّي، وبسقف ثابت. لا إعادة محاولة على `policy_refused` أو `auth_failed`.
- **الاعتماد**: `env:AATM_API_TOKEN` فقط عبر `credential_ref` (نمط AATM نفسه في `credential_policy.py`)، لا يُخزَّن في قاعدة البيانات ولا يُطبع في السجلات.
- **لا عبور للأسرار أو الكوكيز أو رموز الموصل** في أي عقد من الاتجاهين؛ `artifacts` مسارات لا محتويات اعتماد.
- **لا تفويض لمهام تمسّ بيانات اعتماد أو تتطلب تجاوز تحقّق**؛ تُرفض محلياً بـ`policy_refused` قبل الإرسال.

### 20.5 ما لا يفعله المحوّل

لا يشارك ملفات تعريف المتصفح، ولا يمرّر رمز موصل، ولا يستخدم جلسة AATM للوصول إلى Arena بالنيابة عن NEXUS، ولا يخزّن محتوى موجّهات/أجوبة AATM (أطوال وأكواد فقط).

---

## 21. ضمان استقلال نواة NEXUS عن AATM

شرط قبول صريح، ويُترجَم إلى قواعد قابلة للاختبار آلياً:

1. **لا استيراد**: لا يوجد في وحدات النواة أي `import` من `integrations.arena_bridge` أو `integrations.aatm_adapter` (يُختبر بـ`grep`/AST test).
2. **لا اسم في العقد الأساسي**: النواة تعرّف `TaskExchange`/`ArenaTransport` كـ`Protocol` محلي؛ لا ذكر لـ"aatm" في `nexus/core/**`.
3. **دوائر النشر مستقلة**: تعطيل/حذف `integrations/` لا يمنع تشغيل النواة ولا يكسر اختباراتها.
4. **حالات الغياب صريحة**: عند غياب الوحدة/المحوّل تعيد النواة `integration: unavailable` وتستمر، ولا تُظهر خطأ مستخدم.
5. **البوابات مغلقة افتراضياً**: كل مفاتيح §19.3 و§20.3 افتراضياً `false`/فارغة، والتفعيل الحقيقي يتطلب `NEXUS_ARENA_DISCLOSURE_ACK=true` + مراجعة.
6. **لا ادعاء تشغيلي**: توثيق NEXUS يصف الوحدتين بـ«اختيارية / غير مختبرة» حتى توجد نتائج اختبار حقيقية موثّقة.

---

## 22. ملخّص التوصيات

| البند | التوصية |
| --- | --- |
| نسخ أي شيفرة من AATM | ⛔ **لا** — المستودع بلا ترخيص، ولا منح حقوق |
| استخدام AATM كمرجع معماري | ✅ **نعم** — البروتوكول، البوابة المزدوجة، نموذج الحالة، تدقيق السكربت |
| وحدة `NEXUS Arena Bridge` | ✅ **اختيارية، معطّلة افتراضياً**، تنفيذ مستقل، loopback فقط |
| محوّل `AATM Integration Adapter` | ✅ **اختياري، معطّلة افتراضياً**، مع عزل فشل وتصنيف أخطاء مغلق |
| تفريق `awaiting_auth` عن `blocked_human_check` | ✅ **إلزامي** في تصميم NEXUS (إصلاح خلط AATM) |
| ادّعاء أن أي تكامل يعمل | ⛔ **ممنوع** حتى توجد نتائج اختبار موثّقة |
| الاعتماد على `docs/SECURITY.md` في AATM بشأن حدود المعدل | ⛔ **لا** — تناقض مع الشيفرة (§13.3) |

---

## 23. العمل المتبقي قبل أي تنفيذ أو ادّعاء

1. **مراجعة قانونية**: ترخيص AATM غائب؛ أي نسخ/اشتقاق يحتاج إذناً كتابياً من المالك. استقلال التنفيذ المقترح في §19 يقلّل المخاطرة لكنه لا يزيل الالتزام تجاه مشروع MIT الأصلي إن أُعيد استخدام جسم السكربت.
2. **إقرار مشغّل موثّق** لمبدأ الاستخدام عبر المتصفح، مع §18 حرفياً، قبل أي تفعيل حقيقي.
3. **بناء واختبار `states.py`** (جدول الانتقالات) باختبارات وحدات **قبل** أي شبكة — هذا الجزء قابل للاختبار بالكامل بلا متصفح.
4. **جسر مرجعي + صفحة وهمية محلية** (على نمط `bridge/mock_arena/agent.html`) لاختبار `hello`/`config`/`command`/`result` وكل حالات §17 آلياً.
5. **قياس عملي** لحالات الفشل الحقيقية قبل أي وصف للإنتاج: نسبة `awaiting_auth` و`blocked_human_check` و`connector_unavailable` على أصل واحد، لمدة محدّدة، مع سجل.
6. **عقد `TaskExchange`** مع AATM: لا يُوصف بأنه «يعمل» قبل تشغيله بين نظامين حقيقيين وتوثيق النتيجة.
7. **تحديث `docs/SECURITY.md` في AATM** (خارج نطاق هذا المستودع): إزالة سطر «minimum delay / daily cap» أو تنفيذه فعلاً.

---

## 24. فهرس المراجع المسمّاة بالاسم

| الملف | ما يهمّ NEXUS |
| --- | --- |
| `bridge/connector.py` | `ConnectorHub`, `ProfileState`, `register()`, `reset()`, `handle_socket()`, `_authenticate()`, `_on_message()`, `_mark_needs_human()`, `dispatch()`, `command()`, `_validate_command()`, `summaries()`, `register_connector_routes()`, `AGENT_COMMANDS`, `AGENT_STATES`, `DEFAULT_STOP_SELECTORS`, `DEFAULT_STOP_PHRASES`, `README` السطور 1–28 |
| `bridge/server.py` | `create_app()`, `_verify_bearer_auth()`, `chat_completions()`, `health()`, `/mock-arena/`, `/mock-arena/agent/`, `BridgeSessionStore`, `BRIDGE_VERSION="2.4.0"` |
| `bridge/mock_arena/agent.html` | صفحة وكيل وهمية: `Keep working`, `data-aatm-human-check`, `data-aatm-offline` |
| `bridge/tests/test_bridge.py` | 852 سطراً من سيناريوهات الجسر |
| `backend/app/browser/arena_connector.py` | `arena_gate()`, `real_arena_enabled()`, `configured_origins()`, `allowed_origins()`, `match_patterns()`, `mock_url()`, `bridge_ws_url()`, `mint_token()`, `build_userscript()`, `USERSCRIPT_BODY`, `register_profile_with_bridge()`, `bridge_call()`, `ensure_arena_browser_provider()`, `SCRIPT_VERSION="2.3.1"` |
| `backend/app/browser/arena_sessions.py` | `set_arena_mode()`, `sync_profiles_with_bridge()`, `claim_session()`, `apply_bridge_state()`, `bridge_profile_state()`, `session_dict()`, `arena_agent_overview()`, `ArenaSessionConflict` |
| `backend/app/browser/manager.py` | `BrowserManager.launch_profile()`, `_launch_playwright_context()`, `run_userscript()` (501), `get_lock_status()`, `_acquire_file_lock()`, `stop_profile()`, `_guard_browser_request()` |
| `backend/app/browser/engines.py` | `validate_userscript_policy()`, `PROHIBITED_USERSCRIPT_PATTERNS`, `PROHIBITED_GRANT_PATTERN`, `ALLOWED_BROWSER_ACTIONS` |
| `backend/app/browser/safety.py` | `validate_selector()`, `validate_navigation_url()`, `validate_public_navigation_url()`, `redact_extracted_text()`, `PROHIBITED_SELECTOR_RE` |
| `backend/app/browser/install_links.py` | `InstallLinkStore.create()/consume()`, `INSTALL_LINK_TTL_SECONDS=600` |
| `backend/app/api/routes/arena.py` | `connector_status()`, `browser_wall()`, `generate_userscript()`, `create_install_link()`, `use_install_link()`, `_issue_userscript()`, `register_profile()`, `resume_after_human()`, `open_for_sign_in()`, `set_agent_mode()`, `run_profile_command()`, `agent_overview()` |
| `backend/app/providers/adapters/arena_browser.py` · `backend/app/providers/adapters/arena_agent.py` · `backend/app/providers/adapters/arena_bridge.py` | `ArenaBrowserAdapter.health_check/generate`, `ArenaAgentAdapter.command/wait_for_state/submit/keep_working/stop/read_last_reply/selector_test/run_until_quiet`, `ArenaSubmitQueue.slot()`, `redact_reply()`, `ArenaLocalBridgeAdapter.generate/generate_stream/get_session/delete_session` |
| `backend/app/orchestration/{scheduler,arena_runner,manager_arena}.py` | `TaskScheduler.run_orchestration_cycle`, `_arena_disconnected_agent_ids`, `claim_session` integration |
| `backend/app/core/config.py` | كل مفاتيح `ARENA_*` (§11.1) |
| `docs/SECURITY.md` §8 · `docs/SETUP_AR.md` §3–§8 · `THIRD_PARTY_NOTICES.md` · `.github/workflows/ci.yml` | السياسة، التدفق اليدوي، الإسناد، بوابات CI |
| `frontend/src/views/ArenaViews.tsx` | شارات الحالة وزر الاستئناف |
| `backend/tests/test_arena_*.py`, `test_r2_arena_userscript.py`, `test_d_arena_connector.py` | سيناريوهات قابلة للاستلهام (الحالات، الانقطاع، التعافي، إعادة تشغيل الجسر، السكربت) |

---

## 25. القيود المعروفة لهذا التقييم

1. **لا شيء عن `arena.ai` الحقيقي** — لم يُفتح موقع، ولم يُشغَّل سكربت على الأصل الحقيقي. كل ما يتعلق بسلوك الموقع **غير متحقق**.
2. **لم تُشغَّل حزمة اختبارات AATM** (91 ملفاً) — تحتاج متطلبات الـ backend كاملة وقاعدة بيانات؛ الأثر الوحيد المُنفَّذ هو فحص `bridge/connector.py` و`bridge/server.py` (§15).
3. **لم يُنفَّذ أي جزء من تصميمي §19/§20** — لا كود، لا اختبارات.
4. **أرقام الحجم والملفات** مأخوذة من النسخة `1da237f` وقد تتغير.
5. **بنية NEXUS الفعلية** غير متوفرة في هذا المستودع؛ أسماء الوحدات في §19/§20 مقترحة وتحتاج مطابقة.
6. **«البند 12/13 من المواصفة»**: بند 12 في `AATM_MASTER_SPECIFICATION.md` (سطور 586–641) يحدّد 10 نقاط تقييم لكل مشروع + حقول تقرير، ولا يسمّي الجوانب الاثني عشر الواردة في نصّ هذه المهمة؛ لذلك اعتمدت على **نصّ المهمة نفسه** كمرجع للبنود، وأشرت إلى مصدره في المواصفة.
