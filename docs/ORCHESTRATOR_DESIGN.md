# المرحلة 3 — تصميم المنظم والجدولة (Orchestrator + Scheduler)

**المهمة:** AATM-06c3aca9-2eed-48fd-9f89-a70c3a911166
**النطاق:** توثيق تصميمي فقط. لا يُضاف أي كود تطبيقي في هذه المهمة — لا `backend/` ولا مسارات API ولا نماذج تنفيذية. المخرجات هي هذا المستند واختبارات تحقق من بنيته (`tests/test_orchestrator_design.py`).
**التاريخ:** 2026-11-26 (UTC).
**الفرع:** `arena/5ae35693-test-program` من `main` عند `cbc9c69483d7ed7705fd4eba79ab2fbcd57c8219`.

> **لماذا تصميم فقط؟** المرحلة 2 (backbone الخلفية) لم تُدمج بعد؛ كودها قيد المراجعة في الطلبين المفتوحين #8 و#9. البناء فوق كود غير مدمج يخلق تعارضات ويخالف نموذج الملكية والتسليم في AATM («يجب إكمال كل مرحلة قبل البدء في التي تليها» — `docs/ROADMAP.md`). لذلك تغطي هذه المهمة **تصميم** المرحلة 3 بالكامل ليكون جاهزًا للتنفيذ فور دمج المرحلة 2، على نمط مهام التصميم السابقة (#5 لتقييم المزوّد، #7 لتقييم AATM/Arena).

> ### منهجية التحقق
> الحقائق في هذا المستند من نوعين:
> 1. **مُقيدة في المستودع:** `README.md` (نموذج المدير/العمال/المراجع)، `docs/ROADMAP.md` (مخرجات المرحلة 3: «مدير المهام، الجدولة الذرية، عمال AgentLoop (أربعة افتراضيًا)»)، `docs/ENVIRONMENT.md` (لا Docker ‏→ SQLite أولًا)، `.env.example` (`DATABASE_URL=sqlite:///./nexus.db`)، وملفات الطلبين المفتوحين #8/#9 (بنية `backend/app`، جدول `agent_sessions` مع `last_heartbeat_at`، Alembic).
> 2. **مقيسة تجريبيًا في هذه الجلسة:** سلوك الجدولة الذرية على SQLite عبر مسبار فعلي (الملحق أ) شُغّل على Python 3.11.2 وSQLite 3.40.1 (ناتج `python3 -c "import sqlite3; print(sqlite3.sqlite_version)"` في هذه البيئة). النتائج في القسم 5.3.
>
> كل ما لم يُتحقق بإحدى الطريقتين — خصوصًا **أداء المهام الحقيقية (Git/شبكة/نماذج)، وسلوك Postgres، والمطالبات المعتمدة على التبعيات** — موسوم صراحةً بعبارة **«غير متحقق»**. أي أسماء جداول/أعمدة/مسارات API هنا **اقتراحات تصميمية** يجب مطابقتها مع عقد `docs/API.md` وترحيل Alembic من #8/#9 قبل التنفيذ.

---

## 1. المتطلبات (من المواصفة المقيّدة في المستودع)

| # | المتطلب | المصدر |
|---|---|---|
| 1 | مدير يحوّل التوجيهات إلى مهام | `README.md` — نظرة عامة |
| 2 | عمال ينفذون المهام في فروع Git معزولة | `README.md` |
| 3 | مراجع يراجع الطلبات قبل الدمج — العامل لا يدمج أبدًا | `README.md` |
| 4 | جدولة ذرية: لا تُسلَّم المهمة لعاملين في آن واحد | `docs/ROADMAP.md` — المرحلة 3 |
| 5 | عمال AgentLoop، **أربعة افتراضيًا** | `docs/ROADMAP.md` — المرحلة 3 |
| 6 | SQLite قاعدةً افتراضية (لا Docker في البيئة) | `docs/ENVIRONMENT.md` + `.env.example` |
| 7 | تعمل المنظومة بلا ذكاء اصطناعي عند غياب المزوّد (تدهور آمن) | تصميم المزوّد في #5 (`docs/AI_PROVIDER_EVALUATION.md`، غير مدمج) |

**أهداف غير وظيفية:** استرجاع المهام من العمال الموتى بلا تدخل يدوي؛ سجل تدقيق لكل انتقال حالة؛ قابلية التشغيل على مضيف واحد بعدة عمليات؛ حدود موارد مضبوطة بالإعدادات.

**خارج النطاق (مراحل أخرى):** تنفيذ مزوّد النماذج (المرحلة 4)، المتصفح السائق (المرحلة 5)، مسارات الساحة (المرحلة 6)، لوحة القيادة (المرحلة 7)، والحاويات (#11).

---

## 2. المكونات والبنية

```
                 ┌────────────────────────────────────────────────┐
                 │                 backend (FastAPI)              │
  توجيه/مستخدم ──▶  TaskManager (مدير المهام)                     │
                 │    │ إنشاء مهام + أولويات + تبعيات            │
                 │    ▼                                           │
                 │  tasks / task_events  ◀── Scheduler (جدولة)    │
                 │    ▲    │                                        │
                 │    │    │ مطالبة ذرية (claim) + إيجار (lease)   │
                 │  Reaper │                                       │
                 │ (استرجاع)▼                                      │
                 │  AgentLoop × 4 (افتراضيًا)                      │
                 │    │ فرع Git معزول لكل مهمة → commit → push     │
                 │    │ → فتح PR بعنوان [AATM-…]                   │
                 │    ▼                                           │
                 │  بوابة المراجع (Reviewer) — الدمج خارج العمال  │
                 └────────────────────────────────────────────────┘
                          │ (اختياري، مرحلة 4)
                          ▼
                 Provider Router — مسار تدهور آمن بلا AI
```

| المكوّن | المسؤولية | لا يفعل |
|---|---|---|
| **TaskManager** | تحويل توجيه إلى مهمة/مهام، التحقق من الصحة، الأولويات والتبعيات، الإلغاء | لا ينفذ مهام ولا يلمس Git |
| **Scheduler** | تسليم المهمة لعامل واحد بالضبط عبر مطالبة ذرية، وترتيب الأولوية ثم FIFO | لا يقرر محتوى التنفيذ |
| **Reaper** | إعادة المهام منتهية الإيجار إلى الطابور، وتنظيف عند الإقلاع | لا يقتل عمليات؛ الاسترجاع منطقي (DB) |
| **AgentLoop** | حلقة: طالِب → نفّذ في فرع معزول → سلّم PR → حدّث الحالة؛ نبضات وتجديد إيجار | لا يدمج PR ولا يعدّل مهام غيره |
| **Reviewer** | مراجعة PR والموافقة/الرفض؛ الدمج بقراره | خارج نطاق تنفيذ العامل |

فصل المسؤوليات يعني أن الجدولة **لا تعرف شيئًا عن Git أو النماذج**، وأن العامل **لا يعرف شيئًا عن آلية المطالبة** — ينادي دالة `claim()` فقط. هذا يسمح باستبدال SQLite بـ Postgres لاحقًا دون لمس منطق العامل.

---

## 3. نموذج البيانات المقترح

> **تنبيه مطابقة:** الأسماء والأنواع هنا اقتراح تصميمي. عند التنفيذ تُنشأ الجداول عبر ترحيل Alembic وفق بنية #9 (`backend/alembic/versions/…`)، وتُوحَّد الأسماء مع `agent_sessions` الموجودة هناك (مثلًا ربط `worker_id` بجلسة العامل). الجزء «الأساسي» أدناه هو **حرفيًا ما اختُبر في المسبار** (الملحق أ)؛ وما بعده اقتراحات غير مختبرة.

### 3.1 الأساس المُتحقق (كما في المسبار)

```sql
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued','running','succeeded','failed','cancelled')),
    priority INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    worker_id TEXT,
    lease_expires_at REAL,
    attempt INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_tasks_claim ON tasks (status, priority DESC, created_at ASC);
```

- فهرس `idx_tasks_claim` يغطي استعلام المطالبة كاملًا (`WHERE status … ORDER BY priority DESC, created_at ASC`).
- الأزمنة `REAL` (ثوانٍ Unix بتوقيت UTC) — تكفي لمضيف واحد؛ عند تعدد المضيفين لاحقًا تُراجع (القسم 12).

### 3.2 أعمدة إضافية مقترحة (غير متحققة — تُضاف بترحيل لاحق)

| العمود | النوع | الغرض |
|---|---|---|
| `instruction` | `TEXT NOT NULL` | نص التوجيه الأصلي من المدير |
| `payload` | `TEXT` (JSON) | معاملات التنفيذ المنظمة |
| `max_attempts` | `INTEGER DEFAULT 3` | سقف المحاولات قبل الفشل النهائي |
| `not_before` | `REAL` | تأخير إعادة المحاولة (backoff)؛ تُضاف للشرط `AND (not_before IS NULL OR not_before <= :now)` |
| `cancel_requested` | `INTEGER DEFAULT 0` | إلغاء تعاوني يفحصه العامل بين الخطوات |
| `branch_name` | `TEXT` | اسم فرع Git الحتمي `arena/task-<id>` |
| `pr_url` | `TEXT` | رابط طلب السحب الذي فتحه العامل |
| `result` | `TEXT` (JSON) | ملخص النتيجة المسلّمة للمراجع |
| `error` | `TEXT` | سبب آخر فشل |
| `updated_at` | `REAL` | آخر تعديل، يُحدَّث مع كل انتقال |

### 3.3 سجل التدقيق `task_events` (اقتراح)

```sql
CREATE TABLE task_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL REFERENCES tasks(id),
    at REAL NOT NULL,
    actor TEXT NOT NULL,          -- manager | scheduler | worker:<id> | reaper | reviewer
    from_status TEXT,
    to_status TEXT NOT NULL,
    detail TEXT                   -- JSON: سبب، محاولة، فرع، PR…
);
```

يُكتب الحدث **في نفس معاملة** انتقال الحالة (atomicity بين الحالة والسجل)، فلا يمكن أن يظهر انتقال بلا أثر.

### 3.4 التبعيات (اقتراح، غير متحقق)

```sql
CREATE TABLE task_dependencies (
    task_id INTEGER NOT NULL REFERENCES tasks(id),
    depends_on INTEGER NOT NULL REFERENCES tasks(id),
    PRIMARY KEY (task_id, depends_on)
);
```

يرفض المدير أي إدخال يُنشئ دورة (فحص DFS عند الإنشاء). المطالبة المعتمدة على التبعيات في القسم 5.4.

---

## 4. آلة حالات المهمة

```
                 ┌─────────────── إلغاء تعاوني ───────────────┐
                 │                                            ▼
   [إنشاء] ──▶ queued ──مطالبة ذرية──▶ running ──إنهاء──▶ succeeded (نهائية)
                 ▲                        │
                 │                        ├──فشل قابل لإعادة المحاولة──▶ queued (attempt+1 محفوظة،
                 │                        │        (backoff عبر not_before)      مع not_before)
                 │                        │
                 ├──انتهاء الإيجار/موت العامل (Reaper)──┤
                 │                        │
                 │                        └──استنفاد max_attempts──▶ failed (نهائية)
                 └── queued ──إلغاء صريح──▶ cancelled (نهائية)
```

| الانتقال | المنفّذ | الحارس (guard) |
|---|---|---|
| `queued → running` | Scheduler (داخل مطالبة العامل) | المطابقة الذرية (القسم 5) + التبعيات مكتملة + `not_before` حان |
| `running → succeeded` | العامل | `WHERE worker_id=:me AND attempt=:my_attempt AND status='running'` (سياج، القسم 6.4) |
| `running → queued` | Reaper | `status='running' AND lease_expires_at < now` — أو إعادة تشغيل العامل نفسه |
| `running → queued` (إعادة محاولة) | العامل عند فشل قابل للاسترجاع | `attempt < max_attempts`؛ وإلا `failed` |
| `queued → cancelled` | المدير/المستخدم عبر API | الحالة ما تزال `queued` |
| `running → cancelled` | العامل | رأى `cancel_requested=1` بين خطوتين؛ ينظف فرعه ويسجل الحدث |

**قواعد ملزمة:**
- `succeeded` تعني «سُلّم PR للمراجع»، **لا** «دُمج». الدمج قرار المراجع خارج آلة الحالات هذه.
- الحالات النهائية الثلاث لا تُغادر أبدًا؛ أي إعادة تشغيل تعني **مهمة جديدة** تشير إلى السابقة في `detail`.
- `attempt` تزداد عند كل مطالبة (وليس عند كل فشل)، فتبقى محفوظة عبر استرجاع الـ Reaper — لا يمكن لمهمة عالقة أن تدور للأبد لأن حدّ `max_attempts` يُفحص أيضًا عند الاسترجاع (يحوّل الـ Reaper المهمة إلى `failed` إذا استُنفدت المحاولات).

---

## 5. الجدولة الذرية — النواة المُتحققة

### 5.1 لماذا هذا هو القلب؟

المتطلب 4 يعني: تحت أي تزامن، **مطالبة واحدة ناجحة لكل مهمة في كل محاولة**. على SQLite (كاتب واحد في اللحظة) يتحقق ذلك بطريقتين، وكلاهما اختُبر فعليًا (القسم 5.3):

### 5.2 نمطا المطالبة

**النمط A — بيان واحد `UPDATE … RETURNING`** (يتطلب SQLite ≥ 3.35؛ البيئة هنا 3.40.1):

```sql
UPDATE tasks
   SET status = 'running',
       worker_id = :worker_id,
       lease_expires_at = :now + :lease_seconds,
       attempt = attempt + 1
 WHERE id = (
       SELECT id FROM tasks
        WHERE status = 'queued'
        ORDER BY priority DESC, created_at ASC
        LIMIT 1
 )
RETURNING id;
```

البيان ذري بطبيعته: الاستعلام الفرعي والتحديث في معاملة واحدة ضمنية؛ لا نافذة سباق بين القراءة والكتابة. إرجاع صف = نجاح المطالبة؛ إرجاع لا شيء = الطابور فارغ.

**النمط B — `BEGIN IMMEDIATE` + `SELECT` + `UPDATE`** (يعمل على أي SQLite حديث، وهو المسار المحمول):

```sql
BEGIN IMMEDIATE;
SELECT id FROM tasks WHERE status='queued'
 ORDER BY priority DESC, created_at ASC LIMIT 1;
UPDATE tasks SET status='running', worker_id=:worker_id,
       lease_expires_at=:now + :lease_seconds, attempt=attempt+1
 WHERE id=:selected_id AND status='queued';
COMMIT;
```

`BEGIN IMMEDIATE` يحجز قفل الكتابة **قبل** القراءة، فتتسلسل المعاملات المتنافسة ولا يحدث lost-update. الشرط `AND status='queued'` في التحديث دفاع إضافي (لا يضر وإن كان القفل يكفي).

**إعدادات الاتصال الموصى بها (اختُبرت في المسبار):**

```sql
PRAGMA journal_mode=WAL;      -- قرّاء لا يحجبون الكاتب؛ أداء أعلى (5.3)
PRAGMA busy_timeout=5000;     -- انتظار القفل بدل SQLITE_BUSY الفوري
PRAGMA synchronous=NORMAL;    -- مقبول مع WAL لمهام قابلة لإعادة التنفيذ
```

`busy_timeout` **إلزامي** مع عدة عمليات كاتبة؛ بدونه تفشل المطالبات المتنافسة بـ `database is locked` بدل الانتظار.

### 5.3 النتائج المقيسة (مسبار الملحق أ — 2026-11-26)

الإعداد: 8 عمليات عاملة متزامنة (ضعف الافتراضي 4، للضغط)، 200 مهمة، 5 جولات لكل تركيبة، حاجز بدء مشترك، SQLite 3.40.1 على Python 3.11.2، Linux x86_64.

| journal_mode | نمط المطالبة | الجولات | مطالبات ناجحة | ازدواج | مهام ضائعة | زمن الجولة (200 مطالبة) |
|---|---|---|---|---|---|---|
| WAL | A ‏(RETURNING) | 5 | 1000/1000 | **0** | **0** | 0.03–0.07 ث |
| WAL | B ‏(IMMEDIATE) | 5 | 1000/1000 | **0** | **0** | 0.03–0.12 ث |
| DELETE | A ‏(RETURNING) | 5 | 1000/1000 | **0** | **0** | 0.24–0.54 ث |
| DELETE | B ‏(IMMEDIATE) | 5 | 1000/1000 | **0** | **0** | 0.24–0.74 ث |

**الاستنتاجات:**
1. **صفر ازدواج وصفر ضياع في 4000 مطالبة** عبر كل التركيبات — الذرية مثبتة عمليًا للنمطين.
2. WAL أسرع بنحو **5–10×** في هذا الاختبار المصغّر؛ يُعتمد افتراضيًا. (الرقم خاص بهذا المسبار على هذه الآلة — **غير متحقق** لمهام حقيقية ذات أحمال Git/شبكة.)
3. **العدالة ليست مكفولة بهذا النمط وحده**: في بعض الجولات استحوذ عامل واحد على كل المهام لأن حلقة المسبار تطالب بلا تنفيذ بينها. في النظام الحقيقي العامل ينفّذ المهمة (دقائق) بين المطالبتين، فيتوزع العمل طبيعيًا. القاعدة الملزمة: **طالِب مهمة واحدة، نفّذها، ثم طالِب التالية** — لا مطالبة مسبقة لطابور محلي.
4. استرجاع الإيجار (القسم 6) اختُبر في نفس المسبار: أُعيدت 10 مهام منتهية الإيجار بالضبط، وبقيت 10 حية الإيجار `running`، في وضعي WAL وDELETE.

### 5.4 المطالبة مع التبعيات والتأخير (اقتراح — غير متحقق تجريبيًا)

```sql
-- امتداد النمط A؛ لم يُشغَّل في المسبار، يجب اختباره عند التنفيذ
UPDATE tasks
   SET status='running', worker_id=:worker_id,
       lease_expires_at=:now + :lease_seconds, attempt=attempt+1
 WHERE id = (
       SELECT t.id FROM tasks t
        WHERE t.status='queued'
          AND (t.not_before IS NULL OR t.not_before <= :now)
          AND NOT EXISTS (
              SELECT 1 FROM task_dependencies d
              JOIN tasks dep ON dep.id = d.depends_on
              WHERE d.task_id = t.id AND dep.status <> 'succeeded'
          )
        ORDER BY t.priority DESC, t.created_at ASC
        LIMIT 1
 )
RETURNING id;
```

مهمة معلّقة على تبعية فاشلة نهائيًا (`failed`/`cancelled`) لن تُطالب أبدًا؛ يعالج المدير ذلك بسياسة صريحة (فشل التابعة، أو فك التبعية بقرار موثق) — تُحسم عند التنفيذ.

### 5.5 مسار Postgres لاحقًا (غير متحقق — لا Docker في البيئة)

عند تعدد المضيفين يُستبدل نمط المطالبة بـ `SELECT … FOR UPDATE SKIP LOCKED` داخل معاملة، بنفس العقد (`claim() -> Task | None`). لم يُختبر أي من هذا هنا؛ `docs/ENVIRONMENT.md` يقيّد البيئة بلا Docker، والتصميم الحالي **مضيف واحد + SQLite** عمدًا.

---

## 6. الإيجارات والنبضات والتعافي

### 6.1 الإيجار (lease)

كل مطالبة تمنح العامل إيجارًا مدته `NEXUS_LEASE_SECONDS` (افتراضي مقترح **60 ث**). ما دام العامل حيًا يجدد الإيجار بنبضة كل `NEXUS_HEARTBEAT_SECONDS` (افتراضي مقترح **15 ث**):

```sql
UPDATE tasks
   SET lease_expires_at = :now + :lease_seconds
 WHERE id = :task_id AND worker_id = :me AND attempt = :my_attempt
   AND status = 'running';
```

إن لم يُحدَّث أي صف (0 rows affected) فقد العامل ملكيته (استرجعه الـ Reaper أو أُلغيت المهمة) → **يتوقف فورًا** عن أي عمل جانبي (القسم 6.4). هذا يتكامل مع `agent_sessions.last_heartbeat_at` من #9: نبضة العامل تحدّث جلسته والمهمة معًا.

### 6.2 الـ Reaper (مجدول دوري كل `NEXUS_REAPER_INTERVAL_SECONDS`، افتراضي مقترح 10 ث)

```sql
-- مُتحقق في المسبار (القسم 5.3، البند 4)
UPDATE tasks
   SET status='queued', worker_id=NULL, lease_expires_at=NULL
 WHERE status='running' AND lease_expires_at < :now
RETURNING id;
```

مع فحص `attempt >= max_attempts` لكل مسترجَعة: تُحوَّل `failed` بدل `queued` وتُسجَّل في `task_events`. الاسترجاع **منطقي** (صف في DB) ولا يحاول قتل عملية العامل — قد يكون العامل حيًا لكنه متوقف مؤقتًا؛ السياج (6.4) يبطل كتاباته المتأخرة.

### 6.3 التعافي عند الإقلاع

عند إقلاع المنظومة: كل مهمة `running` يتيمة (لا جلسة عامل حية تقابلها وفق `agent_sessions`) تُعاد `queued` فورًا دون انتظار انتهاء الإيجار. هذا يجعل أسوأ زمن استرجاع بعد إعادة تشغيل = زمن الإقلاع، لا 60 ثانية.

### 6.4 السياج (fencing) ضد العامل الزومبي

سيناريو: عامل توقف (GC/تعليق I/O) فانتهى إيجاره واستُرجعت المهمة وطالبتها عملية أخرى؛ ثم استيقظ الأول. بدون حماية قد يكتب نتيجته فوق مهمة يملكها غيره. الحماية: **كل كتابة إنهاء/نبضة مشروطة بـ `(worker_id, attempt)`**:

```sql
UPDATE tasks SET status='succeeded', result=:result, pr_url=:pr_url
 WHERE id=:task_id AND worker_id=:me AND attempt=:my_attempt AND status='running';
```

0 صفوف متأثرة = الملكية ضاعت → يسجل العامل تحذيرًا ويخرج بلا كتابة. `attempt` يعمل رقم سياج (fencing token) يتزايد مع كل مطالبة. (المنطق بسيط ومباشر، لكن سيناريو التوقف/الاستيقاظ الكامل **غير متحقق** تجريبيًا — يُختبر في مرحلة التنفيذ بحقن توقف مُصطنع.)

### 6.5 دلالة التنفيذ: at-least-once

المطالبة exactly-once **لكل محاولة**، لكن التنفيذ الكلي **at-least-once**: قد تُنفَّذ المهمة مرتين إذا مات عامل بعد آثار جانبية. لذلك تُصمم آثار العامل idempotent:
- اسم فرع حتمي `arena/task-<id>` (وليس عشوائيًا)؛ عند إعادة المحاولة يُعاد استخدام الفرع نفسه بـ force-push موثق أو لاحقة `-a<attempt>` بقرار ثابت.
- قبل فتح PR جديد يُبحث عن PR مفتوح لنفس الفرع/العنوان (`[AATM-…]`) ويُحدَّث بدل التكرار.
- لا تُرسل أي آثار خارجية غير قابلة للتكرار (بريد، دفع…) من داخل المهمة أصلًا في هذه المرحلة.

---

## 7. عامل AgentLoop

**العدد الافتراضي: 4** (نص المواصفة في `docs/ROADMAP.md`)، يضبط بـ `NEXUS_WORKER_COUNT`. كل عامل عملية مستقلة (process) بهوية `worker-<n>` + جلسة في `agent_sessions` (#9)، يعمل مهمة واحدة في اللحظة.

### 7.1 الحلقة (pseudo-code توضيحي — ليس كودًا تنفيذيًا)

```
سجّل جلسة العامل (agent_sessions)
حتى إشارة الإيقاف:
    مهمة = claim()                          # القسم 5 — ذرية
    إن لا مهمة: نم backoff قصير (0.5–2 ث بتوقيت متزايد) وواصل
    أنشئ/حدّث الفرع arena/task-<id> من main
    نفّذ خطوات التوجيه:
        - إن cancel_requested: نظّف وسجّل cancelled وتوقف عن المهمة
        - إن ضاعت الملكية (نبضة 0 صفوف): أفلت كل شيء فورًا
        - كل خطوة: نبضة + تجديد إيجار + حدث في task_events
        - المزوّد عبر Provider Router (مرحلة 4)؛ غيابه ⇒ مسار تدهور
          حتمي بلا AI (تحليل ثابت/قوالب) وفق تصميم #5
    ادفع الفرع وافتح PR بعنوان يبدأ بـ [AATM-<task-id>]
    أنهِ المهمة: succeeded (مع pr_url/result) أو failed (مع error)
        # كتابة الإنهاء مشروطة بالسياج (6.4)
عند SIGTERM: أكمل الخطوة الجارية فقط، سلّم ما يمكن تسليمه،
    أعد المهمة queued إن لم تكتمل، أغلق الجلسة، اخرج (مهلة قصوى 30 ث)
```

### 7.2 قواعد ملزمة للعامل

1. **لا يدمج PR أبدًا** — بوابة المراجع (المتطلب 3). `succeeded` = «PR جاهز للمراجعة».
2. **لا يطالب بأكثر من مهمة** في اللحظة (عدالة، القسم 5.3-3).
3. **ميزانية زمنية للمهمة** `NEXUS_TASK_TIMEOUT_SECONDS` (اقتراح 900 ث): عند تجاوزها يفشل المهمة بنفسه (fail-fast) بدل انتظار الـ Reaper؛ الإيجار يبقى شبكة أمان للموت المفاجئ فقط.
4. **إعادة المحاولة**: فشل قابل للاسترجاع (شبكة، مهلة مزوّد) ⇒ `queued` مع `not_before = now + min(300, 2^attempt × 5 + jitter)` ث؛ فشل منطقي (توجيه غير صالح) ⇒ `failed` مباشرة بلا استهلاك محاولات.
5. **عزل Git**: كل العمل داخل الفرع المخصص؛ لا كتابة على `main` ولا على فروع مهام أخرى؛ لا `git push --force` إلا على فرع المهمة نفسه وفق سياسة 6.5.
6. **أسرار**: لا تُكتب مفاتيح في السجلات أو `task_events.detail`؛ القيم الحساسة من `.env` فقط (المقيّد في `docs/ENVIRONMENT.md`).

---

## 8. مدير المهام (TaskManager)

### 8.1 من توجيه إلى مهام

- **الوضع الحتمي (افتراضي، بلا AI)**: توجيه واحد ⇒ مهمة واحدة بعنوان ونص التوجيه كما هما. هذا يضمن عمل النظام كاملًا بلا مزوّد (المتطلب 7).
- **الوضع المدعوم بالنموذج (مرحلة 4، اختياري)**: يقترح المدير تفكيك التوجيه إلى مهام فرعية مع تبعيات؛ **كل تفكيك يمر على نفس تحقق الصحة** ولا يُقبل إلا إذا اجتازه.

### 8.2 تحقق الصحة (ملزم في الوضعين)

| الفحص | الرفض عند |
|---|---|
| عنوان غير فارغ، طول ≤ 200 حرف | غير ذلك ⇒ 422 |
| `priority` عدد صحيح 0–100 | خارج المجال ⇒ 422 |
| التبعيات موجودة ومعروفة | مجهولة ⇒ 404/422 |
| رسم التبعيات دوري | دورة ⇒ 422 مع سلسلة الدورة في الخطأ |
| `max_attempts` بين 1 و10 | خارج المجال ⇒ 422 |

### 8.3 واجهة API مقترحة (تُطابق مع docs/API.md عند التنفيذ)

> **اقتراح غير تعاقدي** — عقد `docs/API.md` يملكه #8/#9؛ تُراجع هذه المسارات وتُوحَّد مع نمط الأخطاء الموحد هناك قبل أي تنفيذ.

| المسار | الطريقة | الغرض |
|---|---|---|
| `/api/tasks` | `POST` | إنشاء مهمة من توجيه (جسم: title, instruction, priority?, depends_on?, max_attempts?) |
| `/api/tasks` | `GET` | سرد مع فلترة `status`/ترقيم صفحات |
| `/api/tasks/{id}` | `GET` | تفاصيل + آخر الأحداث |
| `/api/tasks/{id}/cancel` | `POST` | إلغاء تعاوني: `queued ⇒ cancelled` فورًا؛ `running ⇒ cancel_requested=1` |
| `/api/tasks/{id}/events` | `GET` | سجل التدقيق |
| `/api/workers` | `GET` | جلسات العمال ونبضاتهم (قراءة من `agent_sessions`) |

---

## 9. الإعدادات المقترحة

> تُضاف إلى `.env.example` **عند التنفيذ فقط** (الطلبان #8 و#11 يعدّلان الملف نفسه الآن؛ لم يُلمس في هذه المهمة تفاديًا للتعارض).

| المتغير | الافتراضي المقترح | الوصف |
|---|---|---|
| `NEXUS_WORKER_COUNT` | `4` | عدد عمال AgentLoop (نص المواصفة) |
| `NEXUS_LEASE_SECONDS` | `60` | مدة إيجار المطالبة |
| `NEXUS_HEARTBEAT_SECONDS` | `15` | فترة النبضة/تجديد الإيجار (يجب أن تكون < الإيجار/3) |
| `NEXUS_REAPER_INTERVAL_SECONDS` | `10` | دورية فحص الإيجارات المنتهية |
| `NEXUS_MAX_ATTEMPTS` | `3` | سقف المحاولات الافتراضي لكل مهمة |
| `NEXUS_TASK_TIMEOUT_SECONDS` | `900` | الميزانية الزمنية للمهمة الواحدة |
| `NEXUS_CLAIM_STYLE` | `returning` | `returning` (SQLite ≥ 3.35) أو `immediate` (محمول) |
| `NEXUS_SQLITE_BUSY_TIMEOUT_MS` | `5000` | مهلة انتظار قفل الكتابة |
| `DATABASE_URL` | موجود في `.env.example` | لا تغيير — `sqlite:///./nexus.db` |

قاعدة اشتقاق: `heartbeat × 3 < lease` تمنع استرجاعًا كاذبًا لعامل حي بطيء النبضة؛ يتحقق منها الإعداد عند الإقلاع ويرفض قيمًا متناقضة.

---

## 10. حالات الفشل والتعافي

| الحالة | الكشف | التعافي | الأثر على الدلالة |
|---|---|---|---|
| موت عامل (kill -9 / انهيار) | انتهاء الإيجار / جلسة ميتة عند الإقلاع | Reaper يعيد `queued`؛ السياج يبطل أي كتابة متأخرة | at-least-once (6.5) |
| توقف عامل مؤقتًا (GC/I/O) ثم استيقاظ | نبضة 0 صفوف | العامل يفلت المهمة فورًا؛ المالك الجديد يكمل | لا ازدواج كتابة (سياج) |
| ازدحام كتابة SQLite | `SQLITE_BUSY` بعد busy_timeout | إعادة محاولة المطالبة بـ backoff قصير؛ WAL يقلل الاحتمال | لا فقدان (المطالبة لم تتم) |
| مهمة تفشل منطقيًا | خطأ تنفيذ غير قابل للاسترجاع | `failed` نهائي + `error` + حدث | لا إعادة محاولة عبثية |
| فشل عابر (شبكة/مزوّد) | خطأ قابل للاسترجاع | `queued` + `not_before` backoff؛ `failed` بعد السقف | محاولات محدودة بسقف |
| إقلاع بعد سقوط كامل | مهام `running` بلا جلسات حية | إعادة فورية للطابور (6.3) | الاسترجاع يتم عند الإقلاع |
| PR مكرر من إعادة محاولة | البحث قبل الإنشاء (6.5) | تحديث PR الموجود بدل إنشاء ثانٍ | idempotent تسليم |
| قفزة ساعة المضيف (NTP) | مقارنة أزمنة الإيجار | مضيف واحد + UTC؛ قفزة كبيرة قد تؤخر/تعجّل استرجاعًا — مقبول لأن السياج يحمي الصحة | **غير متحقق** عمليًا؛ يُراجع عند تعدد المضيفين |

---

## 11. قابلية المراقبة

- **سجل أحداث لكل انتقال** (`task_events`) — أساس التدقيق والمراجعة اللاحقة.
- **عدادات دورية تُسجَّل بنيويًا** (structured logging وفق `backend/app/core/logging.py` من #8): عمق الطابور، عدد `running`، معدل النجاح/الفشل، عدد الاسترجاعات، زمن الانتظار (created→claimed) وزمن التنفيذ (claimed→terminal).
- **صحة العمال**: `/api/workers` يعرض نبضات `agent_sessions`؛ عامل بلا نبضة > 3 فترات يُعتبر مشبوهًا في اللوحة (المرحلة 7).
- عتبة إنذار مبكر مقترحة: استرجاعات > 5 في 10 دقائق ⇒ مشكلة نظامية (مزوّد معلق/شبكة) تستحق فحصًا بشريًا.

---

## 12. حدود التصميم وغير المتحقق

1. **مضيف واحد + SQLite فقط**: لا تنسيق عبر مضيفين؛ تعدد المضيفين يتطلب Postgres + `SKIP LOCKED` (5.5) — **غير متحقق** (لا Docker في البيئة، `docs/ENVIRONMENT.md`).
2. **المسبار مصغّر**: مهام فارغة بلا Git/شبكة/نماذج؛ أزمنة 5.3 تخص المطالبة وحدها. إنتاجية النظام الحقيقية **غير متحققة**.
3. **المطالبة مع التبعيات (5.4) والسياج الكامل (6.4) والتعافي عند الإقلاع (6.3)**: منطق مصمم غير مُشغَّل؛ يجب اختبار كل منها بحقن أعطال عند التنفيذ.
4. **الأسماء والعقد**: الجداول/الأعمدة/المسارات اقتراحات؛ المطابقة مع `docs/API.md` وAlembic من #8/#9 **شرط سابق للتنفيذ**.
5. **الأمان**: المصادقة على مسارات المهام ترث مصادقة المرحلة 2 (#8)؛ لا تصميم مصادقة مستقل هنا.
6. **قفزات الساعة والـ DST**: الافتراض UTC + مضيف واحد؛ سلوك القفزات الكبيرة **غير متحقق**.

---

## 13. خطة التنفيذ اللاحقة (بعد دمج المرحلة 2)

| # | خطوة | معيار القبول |
|---|---|---|
| 1 | ترحيل Alembic: `tasks` + `task_events` (+تبعيات) وفق بنية #9 | الترحيل upgrade/downgrade نظيف على SQLite |
| 2 | `Scheduler.claim()` بالنمطين + إعدادات PRAGMA | اختبار تزامن (على نمط الملحق أ) داخل `backend/tests` — 0 ازدواج |
| 3 | Reaper + تعافي الإقلاع + السياج | اختبار حقن موت عامل: المهمة ترجع وتُستكمل، والكتابة المتأخرة مرفوضة |
| 4 | AgentLoop × 4 مع نبضات وإلغاء تعاوني وSIGTERM | اختبار حلقة كاملة بمهمة وهمية (بلا شبكة) من مطالبة حتى `succeeded` |
| 5 | مسارات `/api/tasks…` مطابقة لعقد `docs/API.md` | اختبارات العقد (#9) تغطي المسارات الجديدة |
| 6 | تكامل Git: فرع معزول + PR بعنوان `[AATM-…]` + منع الدمج | اختبار على مستودع مؤقت محلي (bare repo) بلا GitHub فعلي |
| 7 | ربط Provider Router الاختياري + التدهور بلا AI | النظام يكمل مهمة حتمية والمزوّد مفصول |
| 8 | تحديث `.env.example` و`docs/API.md` وCI | CI أخضر شاملًا الاختبارات الجديدة |

---

## الملحق أ — المسبار التجريبي (كما شُغّل حرفيًا في هذه الجلسة)

سكريبت بايثون قياسي فقط (بلا اعتماديات)، أُعيد إنتاج النتائج أدناه بتشغيله على Python 3.11.2 / SQLite 3.40.1. احفظه مثلًا في `/tmp/probe_scheduler.py` وشغّل `python3 /tmp/probe_scheduler.py`.

```python
#!/usr/bin/env python3
"""Empirical probe: atomic task claiming + lease recovery on SQLite (stdlib only).

Verifies the claims made in docs/ORCHESTRATOR_DESIGN.md:
  A) Single-statement claim (UPDATE ... WHERE id = (SELECT ... LIMIT 1) RETURNING)
     yields exactly-once claiming across concurrent worker processes.
  B) BEGIN IMMEDIATE + SELECT + UPDATE alternative also yields exactly-once.
  C) Lease-expiry reaper requeues only expired running tasks.

Runs on both WAL and default DELETE journal modes.
"""
import multiprocessing as mp
import os
import sqlite3
import sys
import tempfile
import time

WORKERS = 8
TASKS = 200
ROUNDS = 5
BUSY_TIMEOUT_MS = 5000

DDL = """
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued','running','succeeded','failed','cancelled')),
    priority INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    worker_id TEXT,
    lease_expires_at REAL,
    attempt INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_tasks_claim ON tasks (status, priority DESC, created_at ASC);
"""

CLAIM_SQL = """
UPDATE tasks
   SET status = 'running',
       worker_id = :worker_id,
       lease_expires_at = :now + :lease_seconds,
       attempt = attempt + 1
 WHERE id = (
       SELECT id FROM tasks
        WHERE status = 'queued'
        ORDER BY priority DESC, created_at ASC
        LIMIT 1
 )
RETURNING id;
"""


def connect(db_path, journal_mode):
    con = sqlite3.connect(db_path, timeout=BUSY_TIMEOUT_MS / 1000)
    con.execute(f"PRAGMA journal_mode={journal_mode}")
    con.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
    con.execute("PRAGMA synchronous=NORMAL")
    return con


def worker_returning(db_path, journal_mode, worker_id, lease_seconds, out_q, barrier):
    con = connect(db_path, journal_mode)
    barrier.wait()
    claimed = []
    while True:
        row = con.execute(
            CLAIM_SQL,
            {"worker_id": worker_id, "now": time.time(), "lease_seconds": lease_seconds},
        ).fetchone()
        con.commit()
        if row is None:
            break
        claimed.append(row[0])
    con.close()
    out_q.put(claimed)


def worker_immediate(db_path, journal_mode, worker_id, lease_seconds, out_q, barrier):
    con = connect(db_path, journal_mode)
    con.isolation_level = None  # manual transaction control
    barrier.wait()
    claimed = []
    while True:
        con.execute("BEGIN IMMEDIATE")
        row = con.execute(
            "SELECT id FROM tasks WHERE status='queued' "
            "ORDER BY priority DESC, created_at ASC LIMIT 1"
        ).fetchone()
        if row is None:
            con.execute("COMMIT")
            break
        con.execute(
            "UPDATE tasks SET status='running', worker_id=?, "
            "lease_expires_at=?, attempt=attempt+1 WHERE id=? AND status='queued'",
            (worker_id, time.time() + lease_seconds, row[0]),
        )
        con.execute("COMMIT")
        claimed.append(row[0])
    con.close()
    out_q.put(claimed)


def run_claim_experiment(journal_mode, claim_style):
    fn = worker_returning if claim_style == "returning" else worker_immediate
    duplicates_total = 0
    unclaimed_total = 0
    for round_no in range(ROUNDS):
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "nexus_probe.db")
            con = connect(db_path, journal_mode)
            con.executescript(DDL)
            now = time.time()
            con.executemany(
                "INSERT INTO tasks (title, priority, created_at) VALUES (?,?,?)",
                [(f"task-{i}", i % 5, now + i * 0.001) for i in range(TASKS)],
            )
            con.commit()
            con.close()

            ctx = mp.get_context("fork")
            out_q = ctx.Queue()
            barrier = ctx.Barrier(WORKERS)
            procs = [
                ctx.Process(target=fn, args=(db_path, journal_mode, f"w{w}", 30.0, out_q, barrier))
                for w in range(WORKERS)
            ]
            t0 = time.perf_counter()
            for p in procs:
                p.start()
            results = [out_q.get() for _ in procs]
            for p in procs:
                p.join()
            elapsed = time.perf_counter() - t0

            all_claims = [tid for chunk in results for tid in chunk]
            duplicates = len(all_claims) - len(set(all_claims))
            unclaimed = TASKS - len(set(all_claims))
            duplicates_total += duplicates
            unclaimed_total += unclaimed
            per_worker = [len(c) for c in results]
            print(
                f"  [{journal_mode:6s} | {claim_style:9s}] round {round_no + 1}/{ROUNDS}: "
                f"claimed={len(all_claims)}/{TASKS} duplicates={duplicates} "
                f"unclaimed={unclaimed} elapsed={elapsed:.2f}s per_worker={per_worker}"
            )
    return duplicates_total, unclaimed_total


def run_lease_recovery(journal_mode):
    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, "nexus_probe.db")
        con = connect(db_path, journal_mode)
        con.executescript(DDL)
        now = time.time()
        # 10 running with expired lease, 10 running with live lease, 5 queued
        rows = []
        for i in range(10):
            rows.append(("expired", "running", now - 60, "dead-worker", now - 5))
        for i in range(10):
            rows.append(("live", "running", now + 60, "live-worker", now + 60))
        for i in range(5):
            rows.append(("queued", "queued", now, None, None))
        con.executemany(
            "INSERT INTO tasks (title, status, created_at, worker_id, lease_expires_at) "
            "VALUES (?,?,?,?,?)",
            rows,
        )
        con.commit()
        reaped = con.execute(
            "UPDATE tasks SET status='queued', worker_id=NULL, lease_expires_at=NULL "
            "WHERE status='running' AND lease_expires_at < :now RETURNING id",
            {"now": now},
        ).fetchall()
        con.commit()
        still_running = con.execute(
            "SELECT COUNT(*) FROM tasks WHERE status='running'"
        ).fetchone()[0]
        queued_now = con.execute(
            "SELECT COUNT(*) FROM tasks WHERE status='queued'"
        ).fetchone()[0]
        con.close()
        ok = len(reaped) == 10 and still_running == 10 and queued_now == 15
        print(
            f"  [{journal_mode:6s} | lease-recovery] reaped={len(reaped)} (expect 10), "
            f"still_running={still_running} (expect 10), queued={queued_now} (expect 15) "
            f"=> {'OK' if ok else 'FAIL'}"
        )
        return ok


def main():
    print(f"Python {sys.version.split()[0]} | SQLite {sqlite3.sqlite_version}")
    print(f"workers={WORKERS} tasks={TASKS} rounds={ROUNDS} busy_timeout={BUSY_TIMEOUT_MS}ms")
    failures = 0
    for jm in ("WAL", "DELETE"):
        for style in ("returning", "immediate"):
            dups, unclaimed = run_claim_experiment(jm, style)
            if dups or unclaimed:
                failures += 1
                print(f"  !! FAIL: duplicates={dups} unclaimed={unclaimed}")
        if not run_lease_recovery(jm):
            failures += 1
    print("RESULT:", "ALL OK" if failures == 0 else f"{failures} FAILURES")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
```

### ملخص الناتج المسجَّل (2026-11-26)

```
Python 3.11.2 | SQLite 3.40.1
workers=8 tasks=200 rounds=5 busy_timeout=5000ms
  [WAL    | returning] كل الجولات: claimed=200/200 duplicates=0 unclaimed=0 (0.03–0.07s)
  [WAL    | immediate] كل الجولات: claimed=200/200 duplicates=0 unclaimed=0 (0.03–0.12s)
  [WAL    | lease-recovery] reaped=10, still_running=10, queued=15 => OK
  [DELETE | returning] كل الجولات: claimed=200/200 duplicates=0 unclaimed=0 (0.24–0.54s)
  [DELETE | immediate] كل الجولات: claimed=200/200 duplicates=0 unclaimed=0 (0.24–0.74s)
  [DELETE | lease-recovery] reaped=10, still_running=10, queued=15 => OK
RESULT: ALL OK
```
