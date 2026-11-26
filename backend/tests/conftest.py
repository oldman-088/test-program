"""بنية اختبارات الخلفية — البند 21 · المهمة AATM-984687b7.

ما يوفّره هذا الملف لكل اختبار:

1. قاعدة SQLite مؤقتة مستقلة (ملف داخل ``tmp_path``) — لا مشاركة ولا ترتيب بين الاختبارات.
2. حقن ``DATABASE_URL`` (وبقية متغيرات البيئة) قبل أي استيراد لوحدة ``app``.
3. عامل بناء ``TestClient`` فوق نفس المصنع الذي يستخدمه النشر (``create_app``).
4. تثبيتات للمخطّطات: عمود/جدول من ``Base.metadata``، ومنشئ إعداد Alembic، وpayloads صالحة/فاسدة.
5. حارس شبكة: أي محاولة اتصال خارج ``127.0.0.1`` تفشل الاختبار — لا نداء خارجي حقيقي.

كل ما هو خارجي (قاعدة إنتاج، خدمات مدفوعة) مُثبَّت أو ممنوع؛ لا ``http`` حقيقي في الاختبارات.
"""

from __future__ import annotations

import os
import shutil
import socket
import sys
import tempfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:  # يعمل ``pytest`` من ``backend/`` ومن جذر المستودع
    sys.path.insert(0, str(BACKEND_DIR))

# ── 1) متغيرات بيئة عالمية قبل استيراد التطبيق ────────────────────────────
# مجلد معزول لملفات SQLite التي قد تنشئها الاستيرادات العرضية (لا ``cwd`` المستخدم).
_GLOBAL_SANDBOX = Path(tempfile.mkdtemp(prefix="aatm-pytest-"))
os.environ["DATABASE_URL"] = f"sqlite:///{_GLOBAL_SANDBOX / 'import-time.db'}"
os.environ["ENVIRONMENT"] = "test"
os.environ["DEBUG"] = "false"
os.environ["LOG_LEVEL"] = "CRITICAL"
os.environ["API_KEY"] = "global-import-time-key"
os.environ["CORS_ALLOW_ORIGINS"] = ""
# لا ملف ``.env`` شخصي يتسرّب إلى Suite كاملة.
os.environ.pop("ENV_FILE", None)

from app.core.config import Settings, clear_settings_cache  # noqa: E402
from app.core.database import Database  # noqa: E402
from app.core.errors import DatabaseUnavailableError  # noqa: E402
from app.main import create_app  # noqa: E402

clear_settings_cache()

#: مفتاح الاختبار الموحّد — كل نقاط العمل محميّة به (القاعدة Q5).
TEST_API_KEY = "test-api-key-0123456789"

#: معرّف جلسة وهمي صالح الشكل — تُستعمله اختبارات العقد لملء `{session_id}`.
UNKNOWN_SESSION_ID = "ses_00000000000000000000"


def pytest_unconfigure(config: pytest.Config) -> None:  # pragma: no cover - تنظيف
    shutil.rmtree(_GLOBAL_SANDBOX, ignore_errors=True)


# ── 2) عزل متغيرات البيئة لكل اختبار ─────────────────────────────────────
@pytest.fixture(autouse=True)
def isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """يحقن ``DATABASE_URL`` لقاعدة هذا الاختبار وحده قبل أن يقرأها أي كائن."""
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'env-injected.db'}")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("LOG_LEVEL", "CRITICAL")
    monkeypatch.setenv("API_KEY", "env-injected-test-key")
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "")
    clear_settings_cache()


#: أسماء متغيرات البيئة التي يقرأها ``Settings`` — تُنظَّف قبل اختبارات الأولوية.
SETTINGS_ENV_VARS: tuple[str, ...] = (
    "APP_NAME",
    "ENVIRONMENT",
    "DEBUG",
    "LOG_LEVEL",
    "DATABASE_URL",
    "DB_POOL_TIMEOUT_SECONDS",
    "DEFAULT_PAGE_SIZE",
    "MAX_PAGE_SIZE",
    "API_V1_PREFIX",
    "REQUEST_ID_HEADER",
    "API_KEY",
    "CORS_ALLOW_ORIGINS",
)


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """يزيل كل متغيرات بيئة الإعدادات: ما يبقى هو الافتراضيات النقية وحدها."""
    for name in SETTINGS_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


# ── 3) حارس الشبكة ────────────────────────────────────────────────────────
_ALLOWED_SOCKET_TARGETS = frozenset({"127.0.0.1", "::1", "localhost", ""})


@pytest.fixture(autouse=True)
def no_external_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """يمنع أي ``connect`` إلى عنوان خارج الحلقة المحلية (``TestClient`` لا يحتاج منفذاً)."""
    real_connect = socket.socket.connect

    def guarded_connect(self: socket.socket, address: object, *args: object, **kwargs: object) -> None:
        host = ""
        if isinstance(address, tuple) and address:
            host = address[0].decode() if isinstance(address[0], bytes) else str(address[0])
        if host in _ALLOWED_SOCKET_TARGETS:
            real_connect(self, address, *args, **kwargs)  # type: ignore[arg-type]
            return
        raise AssertionError(
            "اختبار حاول فتح شبكة حقيقية "
            f"({host!r}). كل نداء خارجي يجب أن يكون مزوّراً (mock) داخل الاختبارات."
        )

    monkeypatch.setattr(socket.socket, "connect", guarded_connect, raising=False)


# ── 4) التثبيتات الأساسية ─────────────────────────────────────────────────
def make_settings(**overrides: object) -> Settings:
    """يبني إعدادات معزولة: لا ``.env`` ولا ملف تعريف، والقيم من الوسائط فقط."""
    base: dict[str, object] = {
        "environment": "test",
        "debug": False,
        "api_key": TEST_API_KEY,
    }
    base.update(overrides)
    return Settings(_env_file=None, **base)  # type: ignore[call-arg]


@pytest.fixture
def temp_database_url(tmp_path: Path) -> str:
    return f"sqlite:///{tmp_path / 'schema.db'}"


@pytest.fixture
def settings(temp_database_url: str) -> Settings:
    return make_settings(database_url=temp_database_url)


@pytest.fixture
def database(settings: Settings) -> Iterator[Database]:
    """قاعدة مؤقتة بمخطط كامل (``create_all`` من النماذج) — تُغلق في النهاية."""
    instance = Database(settings.database_url, echo=False)
    instance.create_all()
    try:
        yield instance
    finally:
        instance.dispose()


@pytest.fixture
def bare_database_url(tmp_path: Path) -> str:
    """ملف منفصل عن ``temp_database_url`` حتى لا تتسرّب جداول تثبيتٍ إلى آخر."""
    return f"sqlite:///{tmp_path / 'bare.db'}"


@pytest.fixture
def bare_database(bare_database_url: str) -> Iterator[Database]:
    """قاعدة مؤقتة بلا أي جدول — لمسارات الفشل (ترحيل لم يُجرَ بعد)."""
    instance = Database(bare_database_url, echo=False)
    try:
        yield instance
    finally:
        instance.dispose()


@pytest.fixture
def make_client(settings: Settings, database: Database) -> Callable[..., Iterator[TestClient]]:
    """عامل يبني تطبيقاً كاملاً (نفس ``create_app`` المستخدم في النشر) فوق قاعدة مُمرّرة صراحةً."""

    @contextmanager
    def _factory(
        *,
        app_settings: Settings | None = None,
        app_database: Database | None = None,
        raise_server_exceptions: bool = False,
    ) -> Iterator[TestClient]:
        app = create_app(app_settings or settings, database=app_database or database)
        with TestClient(app, raise_server_exceptions=raise_server_exceptions) as client:
            yield client

    return _factory


@pytest.fixture
def client(make_client: Callable[..., Iterator[TestClient]]) -> Iterator[TestClient]:
    """عميل جاهز على قاعدة مُهيّأة المخطط مع مفتاح اختبار مضبوط في الإعدادات."""
    with make_client() as client_instance:
        yield client_instance


@pytest.fixture
def empty_client(
    make_client: Callable[..., Iterator[TestClient]],
    bare_database: Database,
) -> Iterator[TestClient]:
    """عميل على قاعدة بلا جداول — لمسار ``503`` وفحوص الترحيل عبر HTTP."""
    with make_client(app_database=bare_database) as client_instance:
        yield client_instance


@pytest.fixture
def bare_alembic_config() -> object:
    """``Config`` بلا ``sqlalchemy.url`` — لاختبار السقوط إلى متغير البيئة ``DATABASE_URL``."""
    from alembic.config import Config

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", "")
    cfg.attributes["configure_logger"] = False
    return cfg


@pytest.fixture
def ping_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """يزوّر انقطاع الاتصال بالقاعدة بدل إسقاط خدمة حقيقية (مسار ``503``)."""

    def boom(self: Database) -> bool:
        raise DatabaseUnavailableError("mocked: connection refused")

    monkeypatch.setattr(Database, "ping", boom, raising=True)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"X-API-Key": TEST_API_KEY}


@pytest.fixture
def session_payload() -> dict[str, str]:
    """جسم صالح موثّق لـ ``POST /api/v1/sessions`` (حالة النجاح)."""
    return {
        "task_id": "984687b7-f4d3-4a4b-8058-1cda372673fa",
        "employee_id": "worker-7",
        "branch": "arena/test-984687b7",
        "worktree": "/worktrees/arena-test-984687b7",
    }


@pytest.fixture
def invalid_session_payload() -> dict[str, object]:
    """جسم فاسد موثّق: ``task_id`` أقصر من الحد، و``employee_id`` فارغ، وحقل زائد."""
    return {"task_id": "short", "employee_id": "   ", "branch": "b", "unexpected": 1}


@pytest.fixture
def created_session(client, auth_headers, session_payload) -> dict[str, str]:
    """جلسة موجودة فعلاً — لتثبيت حالة النجاح في اختبارات القراءة والحذف."""
    response = client.post("/api/v1/sessions", json=session_payload, headers=auth_headers)
    assert response.status_code == 201, response.text
    return response.json()


# ── 5) تثبيتات المخطّطات ──────────────────────────────────────────────────
@pytest.fixture(scope="session")
def sql_schema() -> dict[str, list[str]]:
    """الجدول → أعمدته، من ``Base.metadata`` (لا من قاعدة حقيقية)."""
    import app.models  # noqa: F401  — تسجيل النماذج
    from app.core.database import Base

    return {
        table.name: sorted(column.name for column in table.columns)
        for table in Base.metadata.sorted_tables
    }


@pytest.fixture
def alembic_config(temp_database_url: str) -> Callable[[str], object]:
    """ينشئ ``alembic.config.Config`` موجهاً ``script_location`` إلى ``backend/alembic``."""

    def _factory(url: str | None = None) -> object:
        from alembic.config import Config

        cfg = Config(str(BACKEND_DIR / "alembic.ini"))
        cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
        # يتجاوز متغير البيئة عمداً: الاختبار يحدد قاعدته بنفسه.
        cfg.set_main_option("sqlalchemy.url", url or temp_database_url)
        cfg.attributes["configure_logger"] = False
        return cfg

    return _factory
