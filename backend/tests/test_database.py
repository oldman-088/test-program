"""اختبارات طبقة قاعدة البيانات والترحيل — ``backend/tests/test_database.py`` · البند 21.

حالات النجاح الموثّقة              حالات الفشل الموثّقة
============================  ==================================================
``test_create_all``           إنشاء الجداول من النماذج يطابق المخطّط الموثّق.
``test_crud_cycle``           دورة إنشاء/قراءة/حذف جلسة عبر HTTP ثم المستودع.
``test_alembic_upgrade``      ``upgrade head`` على قاعدة مؤقتة = مخطّط النماذج.
``test_alembic_round_trip``   نزولاً درجة‑درجة يزيل العمود ثم الجدول، ثم يعود صعوداً.
``test_readiness_up``         ``/health/ready`` تُرجع 200 حين تردّ القاعدة.
============================  ==================================================
``test_duplicate_task_id``    تكرار ``task_id`` ⇒ 409 ``conflict`` بالجسم الموحّد.
``test_integrity_error``      تخطّي المستودع ⇒ ``IntegrityError`` وتراجع نظيف.
``test_rollback_on_error``    استثناء بعد الكتابة ⇒ 500 ولا صفّ نصف محفوظ.
``test_readiness_down``       قاعدة لا تردّ (مزوّرة) ⇒ 503، لا 200 كاذبة.
``test_unknown_revision``     رقم هجرة مجهول يفشل قبل أي كتابة على القاعدة.
============================  ==================================================

كل اختبار على ملف SQLite مستقل داخل ``tmp_path`` (يوفره ``conftest``). الترحيل يعمل
على الملف المحلي مباشرةً — لا خادم قاعدة ولا شبكة؛ وفشل الاتصال مُزوَّر بـ``ping_fails``.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.core.database import Database
from app.core.errors import NotFoundError
from app.models import SESSION_STATUSES, AgentSession
from app.repositories import SessionRepository
from conftest import BACKEND_DIR

TABLE = "agent_sessions"
#: جدول Alembic الإداري ليس جزءاً من عقد التطبيق، لكنه موجود بعد أي ترحيل.
ADMIN_TABLES = frozenset({"alembic_version"})


def business_tables(database: Database) -> list[str]:
    return [name for name in database.table_names() if name not in ADMIN_TABLES]


# ─────────────────────── إنشاء الجداول من النماذج ───────────────────────────


def test_create_all_matches_model_schema(database: Database, sql_schema: dict[str, list[str]]) -> None:
    """حالة نجاح: ``create_all`` يُنشئ الجدول بكل أعمدة النموذج وبلا جداول زائدة."""
    assert business_tables(database) == [TABLE]
    assert sorted(database.column_names(TABLE)) == sql_schema[TABLE]
    assert "last_heartbeat_at" in database.column_names(TABLE)


def test_bare_database_has_no_tables(bare_database: Database) -> None:
    """حالة فشل موثّقة: قاعدة مؤقتة بلا ترحيل = لا جداول، فلا نتائج كاذبة لاحقاً."""
    assert bare_database.table_names() == []
    assert bare_database.column_names(TABLE) == []


def test_indexes_and_constraints_use_the_naming_convention(database: Database) -> None:
    """القيود مُسمّاة باتفاقيات ``NAMING_CONVENTION`` — شرط أن ينجح ``downgrade``."""
    insp = inspect(database.engine)
    unique_names = {uq["name"] for uq in insp.get_unique_constraints(TABLE)}
    index_names = {ix["name"] for ix in insp.get_indexes(TABLE)}
    pk = insp.get_pk_constraint(TABLE)

    assert "uq_agent_sessions_task_id" in unique_names
    assert "ix_agent_sessions_employee_status" in index_names
    assert pk["constrained_columns"] == ["id"]
    assert pk["name"] == "pk_agent_sessions"


# ─────────────────────── دورة إنشاء / قراءة / حذف ───────────────────────────


def test_session_crud_cycle_over_http(
    client: TestClient,
    auth_headers: dict[str, str],
    session_payload: dict[str, str],
) -> None:
    """حالة نجاح كاملة: 201 ثم 200 ثم 204 ثم 404 على نفس السجل."""
    created = client.post("/api/v1/sessions", json=session_payload, headers=auth_headers)
    assert created.status_code == 201, created.text
    body = created.json()
    session_id = body["id"]
    assert session_id.startswith("ses_")
    assert body["status"] == "queued"
    assert body["attempts"] == 0
    assert body["task_id"] == session_payload["task_id"]

    fetched = client.get(f"/api/v1/sessions/{session_id}", headers=auth_headers)
    assert fetched.status_code == 200, fetched.text
    assert fetched.json() == body

    listed = client.get("/api/v1/sessions", params={"employee_id": "worker-7"}, headers=auth_headers)
    assert listed.status_code == 200
    assert [row["id"] for row in listed.json()] == [session_id]

    deleted = client.delete(f"/api/v1/sessions/{session_id}", headers=auth_headers)
    assert deleted.status_code == 204
    assert deleted.content == b""

    missing = client.get(f"/api/v1/sessions/{session_id}", headers=auth_headers)
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_found"


def test_session_repository_cycle_on_database(database: Database) -> None:
    """نفس الدورة على مستوى المستودع — تثبت أن السلوك ليس قناع HTTP."""
    with database.session() as session:
        repo = SessionRepository(session)
        record = repo.create(
            task_id="task-crud-000001",
            employee_id="worker-1",
            branch="arena/task-crud",
            worktree=None,
        )
        created_id = record.id
        assert repo.get(created_id).status == "queued"

    with database.session() as session:
        SessionRepository(session).mark_status(created_id, "running")

    with database.session() as session:
        repo = SessionRepository(session)
        reloaded = repo.get(created_id)
        assert reloaded.status == "running"
        assert reloaded.updated_at >= reloaded.created_at
        repo.delete(created_id)

    with database.session() as session:
        repo = SessionRepository(session)
        assert repo.get_by_task_id("task-crud-000001") is None
        with pytest.raises(NotFoundError) as excinfo:
            repo.get(created_id)
        assert excinfo.value.status_code == 404
        assert excinfo.value.code == "not_found"


def test_written_rows_survive_across_sessions(bare_database: Database) -> None:
    """الحفظ حقيقي: جلسة أخرى ترى الصفّ بعد ``commit`` (سياق ``session()`` يُثبّت)."""
    bare_database.create_all()
    with bare_database.session() as session:
        created = SessionRepository(session).create(
            task_id="task-durable-01", employee_id="worker-2", branch="arena/durable"
        )
        durable_id = created.id

    with bare_database.session() as other:
        assert SessionRepository(other).get(durable_id).employee_id == "worker-2"


# ─────────────────────────── حالات الفشل ───────────────────────────────────


def test_duplicate_task_id_conflicts(
    client: TestClient,
    auth_headers: dict[str, str],
    session_payload: dict[str, str],
) -> None:
    """حالة فشل موثّقة: نفس ``task_id`` مرتين ⇒ 409 ``conflict`` بالجسم الموحّد."""
    assert client.post("/api/v1/sessions", json=session_payload, headers=auth_headers).status_code == 201

    second = client.post("/api/v1/sessions", json=session_payload, headers=auth_headers)
    assert second.status_code == 409
    error = second.json()["error"]
    assert error["code"] == "conflict"
    assert error["details"] == []
    assert error["request_id"]

    listed = client.get("/api/v1/sessions", params={"employee_id": "worker-7"}, headers=auth_headers)
    assert len(listed.json()) == 1, "المحاولة الثانية يجب ألا تترك أثراً"


def test_delete_missing_session_is_404(client: TestClient, auth_headers: dict[str, str]) -> None:
    """حذف ما لا وجود له ⇒ 404، ولا يستحدث سجلاً ولا يغيّر المخطّط."""
    response = client.delete(f"/api/v1/sessions/{'ses_' + '0' * 20}", headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert business_tables(client.app.state.database) == [TABLE]  # type: ignore[attr-defined]


def test_unique_index_is_enforced_below_the_repository(database: Database) -> None:
    """حالة فشل موثّقة: تخطّي المستودع ⇒ القيد يرفض، والتراجع يُنظّف كله."""
    with pytest.raises(IntegrityError):
        with database.session() as session:
            session.add(
                AgentSession(
                    task_id="task-race-000001", employee_id="w", branch="b", status="queued"
                )
            )
            session.flush()
            session.add(
                AgentSession(
                    task_id="task-race-000001", employee_id="w2", branch="b2", status="queued"
                )
            )
            session.flush()

    with database.session() as session:
        assert session.query(AgentSession).all() == []


def test_request_error_rolls_back_and_returns_500(
    client: TestClient,
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """حالة فشل موثّقة: استثناء بعد الكتابة داخل الطلب ⇒ 500 ولا صفّ يتسرّب."""

    def write_then_explode(self: SessionRepository, **kwargs: str) -> AgentSession:
        SessionRepository.create(self, **kwargs)  # flush حقيقي داخل نفس المعاملة
        raise RuntimeError("boom: internal failure after flush")

    monkeypatch.setattr(SessionRepository, "create", write_then_explode)
    response = client.post(
        "/api/v1/sessions",
        json={"task_id": "task-rollback-001", "employee_id": "worker-9", "branch": "arena/boom"},
        headers=auth_headers,
    )
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "boom" not in response.text, "لا يُسرَّب نص الاستثناء الداخلي"

    monkeypatch.undo()
    with client.app.state.database.session() as session:  # type: ignore[attr-defined]
        assert SessionRepository(session).get_by_task_id("task-rollback-001") is None


def test_unauthenticated_requests_are_rejected(client: TestClient) -> None:
    """فشل موثّق (القاعدة Q5): بلا مفتاح ⇒ 401، والقائمة لا تُقرأ."""
    response = client.get("/api/v1/sessions", params={"employee_id": "worker-7"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthenticated"


# ──────────────────────────── فحص الجاهزية ────────────────────────────


def test_readiness_up_on_live_database(client: TestClient) -> None:
    """حالة نجاح: القاعدة تردّ ⇒ 200 ``{"status":"ready"}``."""
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "up"}


def test_readiness_down_when_ping_fails(client: TestClient, ping_fails: None) -> None:
    """حالة فشل موثّقة (مزوّرة): قاعدة لا تردّ ⇒ 503 ``database_unavailable``."""
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 503
    error = response.json()["error"]
    assert error["code"] == "database_unavailable"
    assert error["request_id"]


def test_liveness_ignores_the_database(empty_client: TestClient, ping_fails: None) -> None:
    """``/health`` يبقى 200 بلا جداول وباتصال مزوَّر بالفشل — لا يُطفأ مع القاعدة."""
    assert empty_client.app.state.database.table_names() == []  # type: ignore[attr-defined]
    assert empty_client.get("/api/v1/health").status_code == 200
    assert empty_client.get("/api/v1/health/ready").status_code == 503


# ───────────────────────── ترحيل Alembic ───────────────────────────


@pytest.mark.slow
def test_alembic_upgrade_head_builds_the_documented_schema(
    alembic_config, temp_database_url: str, sql_schema: dict[str, list[str]]
) -> None:
    """حالة نجاح: الترحيل الصاعد يعطي مخطّط النماذج نفسه، ويسجّل الرأس 0002."""
    from alembic.script import ScriptDirectory

    from alembic import command

    command.upgrade(alembic_config(temp_database_url), "head")

    migrated = Database(temp_database_url)
    try:
        assert business_tables(migrated) == [TABLE]
        assert sorted(migrated.column_names(TABLE)) == sql_schema[TABLE]
        assert "alembic_version" in migrated.table_names()
        # الجدول الإداري يحمل الرأس الحالي فقط — لا بيانات تطبيق فيه.
        assert migrated.column_names("alembic_version") == ["version_num"]
    finally:
        migrated.dispose()

    script = ScriptDirectory.from_config(alembic_config(temp_database_url))
    assert script.get_heads() == ["0002"]
    assert [rev.revision for rev in script.walk_revisions()] == ["0002", "0001"]


@pytest.mark.slow
def test_alembic_round_trip_up_then_down_on_temp_db(alembic_config, temp_database_url: str) -> None:
    """الإثبات المطلوب: صعوداً ثم نزولاً على قاعدة مؤقتة، ثم إعادة الصعود تعمل."""
    from alembic import command

    cfg = alembic_config(temp_database_url)
    db = Database(temp_database_url)
    try:
        # ── صعوداً درجة‑درجة ──
        command.upgrade(cfg, "0001")
        assert business_tables(db) == [TABLE]
        assert "last_heartbeat_at" not in db.column_names(TABLE)

        command.upgrade(cfg, "head")
        assert "last_heartbeat_at" in db.column_names(TABLE)

        # البيانات تعيش الترقية التصاعدية (``batch_alter_table`` يعيد بناء الجدول).
        with db.session() as session:
            SessionRepository(session).create(
                task_id="task-survive-0001", employee_id="worker-3", branch="arena/survive"
            )
        with db.session() as session:
            assert SessionRepository(session).get_by_task_id("task-survive-0001") is not None
            row_before_downgrade = session.execute(
                text("SELECT task_id, status FROM agent_sessions WHERE task_id = :t"),
                {"t": "task-survive-0001"},
            ).all()

        # ── نزولاً درجة: العمود يختفي والجدول وبياناته يبقيان ──
        command.downgrade(cfg, "0001")
        assert business_tables(db) == [TABLE]
        assert "last_heartbeat_at" not in db.column_names(TABLE)
        # SQL خام عمداً: النموذج أوسع من الجدول بعد النزول، وال ORM سيرفض الأعمدة الناقصة.
        with db.engine.connect() as conn:
            rows_after_downgrade = conn.execute(
                text("SELECT task_id, status FROM agent_sessions WHERE task_id = :t"),
                {"t": "task-survive-0001"},
            ).all()
        assert rows_after_downgrade == row_before_downgrade

        # ── نزولاً إلى الأساس: كل شيء يختفي ──
        command.downgrade(cfg, "base")
        assert business_tables(db) == []

        # ── إعادة الصعود بعد النزول (الهجرة قابلة للتكرار) ──
        command.upgrade(cfg, "head")
        assert sorted(db.column_names(TABLE)) == sorted(sql_columns_of_model())
    finally:
        db.dispose()


def sql_columns_of_model() -> list[str]:
    """أعمدة الجدول من تعريف النموذج — مرجع مستقل عن قاعدة مُهيَّأة."""
    import app.models  # noqa: F401
    from app.core.database import Base

    return sorted(column.name for column in Base.metadata.tables[TABLE].columns)


@pytest.mark.slow
def test_alembic_offline_mode_emits_sql_without_connecting(
    alembic_config, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """وضع ``--sql`` يولّد نص الترحيل على stdout ولا يفتح أي اتصال بقاعدة."""
    from alembic import command

    never_created = tmp_path / "offline-target.db"
    assert command.upgrade(alembic_config(f"sqlite:///{never_created}"), "head", sql=True) is None

    printed = capsys.readouterr().out
    assert "CREATE TABLE agent_sessions" in printed
    assert "INSERT INTO alembic_version" in printed or "alembic_version" in printed
    assert not never_created.exists(), "وضع offline يجب ألا يلمس القاعدة"


@pytest.mark.slow
def test_alembic_falls_back_to_database_url_env(
    bare_alembic_config, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """حالة نجاح لسلسلة الأولوية: ``sqlalchemy.url`` فارغة ⇒ يُقرأ ``DATABASE_URL``."""
    from alembic import command

    url = f"sqlite:///{tmp_path / 'from-env.db'}"
    monkeypatch.setenv("DATABASE_URL", url)

    command.upgrade(bare_alembic_config, "head")

    db = Database(url)
    try:
        assert business_tables(db) == [TABLE]
    finally:
        db.dispose()


@pytest.mark.slow
def test_migrations_leave_no_pending_changes(alembic_config, temp_database_url: str) -> None:
    """لا هجرة منسية: بعد ``upgrade head`` لا فرق بين الهجرات والنماذج."""
    from alembic.migration import MigrationContext

    import app.models  # noqa: F401
    from alembic import autogenerate, command
    from app.core.database import Base

    command.upgrade(alembic_config(temp_database_url), "head")

    db = Database(temp_database_url)
    try:
        with db.engine.connect() as conn:
            context = MigrationContext.configure(
                conn, opts={"target_metadata": Base.metadata, "compare_type": True}
            )
            diffs = autogenerate.compare_metadata(context, Base.metadata)
    finally:
        db.dispose()

    significant = [diff for diff in diffs if not (len(diff) >= 2 and diff[0] in {"modify_index", "add_index"})]
    assert significant == [], f"النماذج أبعد من الهجرات: {significant}"


@pytest.mark.slow
def test_unknown_revision_fails_before_writing(alembic_config, temp_database_url: str) -> None:
    """حالة فشل موثّقة: رقم هجرة مجهول ⇒ خطأ قبل أي كتابة، والمخطّط يبقى فارغاً."""
    from alembic.util.exc import CommandError

    from alembic import command

    with pytest.raises(CommandError):
        command.upgrade(alembic_config(temp_database_url), "9999_does_not_exist")

    db = Database(temp_database_url)
    try:
        # لا جدول تطبيق كُتب: الفشل كان قبل أي تنفيذ (الجدول الإداري وحده قد يبقى).
        assert business_tables(db) == []
    finally:
        db.dispose()


@pytest.mark.slow
def test_revision_template_renders_a_loadable_migration(
    alembic_config, tmp_path: Path
) -> None:
    """حالة نجاح موثّقة للقالب نفسه: ``alembic revision`` يولّد ملفاً يُحمَّل فعلاً.

    تمنع هذه الاختبارَ الانتكاسةَ إلى ``${down_revision | comma,nodes}`` — مرشّح
    غير موجود، وكان يفشل كل توليد هجرة بخطأ في قالب ``script.py.mako``.
    """
    import py_compile

    from alembic import command

    project = tmp_path / "alembic-proj"
    shutil.copytree(BACKEND_DIR / "alembic", project)
    cfg = alembic_config(f"sqlite:///{tmp_path / 'template.db'}")
    cfg.set_main_option("script_location", str(project))

    command.revision(cfg, message="template smoke")

    generated = sorted((project / "versions").glob("*template_smoke.py"))
    assert len(generated) == 1, "لم يُولَّد ملف هجرة من القالب"
    py_compile.compile(str(generated[0]), doraise=True)
    text = generated[0].read_text(encoding="utf-8")
    assert "down_revision: str | Sequence[str] | None = \'0002\'" in text, text
    assert "def upgrade() -> None:" in text and "def downgrade() -> None:" in text
    assert "revision: str = " in text


def test_session_statuses_are_persisted_verbatim(database: Database) -> None:
    """كل حالة موثّقة في ``docs/API.md`` §4 تُخزَّن كما هي (لا ترجمة صامتة)."""
    with database.session() as session:
        repo = SessionRepository(session)
        for index, status in enumerate(SESSION_STATUSES):
            record = repo.create(task_id=f"task-status-{index:06d}", employee_id="w", branch="b")
            repo.mark_status(record.id, status)

    with database.session() as session:
        repo = SessionRepository(session)
        for index, status in enumerate(SESSION_STATUSES):
            stored = repo.get_by_task_id(f"task-status-{index:06d}")
            assert stored is not None
            assert stored.status == status
