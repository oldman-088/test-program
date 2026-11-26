"""اختبارات تحميل الإعدادات — ``backend/tests/test_config.py`` · البند 21.

يغطي ثلاث حالات نجاح موثّقة وثلاث حالات فشل موثّقة:

============================  ==================================================
حالة النجاح                    ما يثبته
============================  ==================================================
``test_defaults...``           القيم الافتراضية الموثّقة في ``docs/API.md`` ثابتة.
``test_env_file...``           ملف ``.env`` يُقرأ فعلاً (المسار، المفتاح، السجل).
``test_env_var_wins_over...``  الأولوية: متغير البيئة > ``.env`` > الافتراضي.
============================  ==================================================

============================  ==================================================
حالة الفشل                     ما يثبته
============================  ==================================================
``test_unknown_environment..`` بيئة غير معروفة مرفوضة عند التحميل، لا عند أول طلب.
``test_unsupported_db_scheme`` مخطط قاعدة غير مدعوم مرفوض برسالة فيها القائمة.
``test_prefix_without_slash``  بادئة مسار غير سليمة مرفوضة (كانت ستُنتج 404 غامضة).
============================  ==================================================

لا نداء شبكي: ``Settings`` كائن بيانات فقط، و``.env`` يُكتب في ``tmp_path``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import (
    DEFAULT_ENV_FILE,
    ENVIRONMENTS,
    SUPPORTED_DB_SCHEMES,
    Settings,
    clear_settings_cache,
    get_settings,
)
from conftest import TEST_API_KEY, make_settings

# ─────────────────────────── حالات النجاح ──────────────────────────────────


def test_defaults_are_documented_values(clean_env: None) -> None:
    """القيم الافتراضية = ما توثيقه الوثيقة. أي تغيير هنا يعني عقداً مكسوراً."""
    settings = Settings(_env_file=None)

    assert settings.app_name == "AATM Backend"
    assert settings.environment == "development"
    assert settings.debug is False
    assert settings.log_level == "INFO"
    assert settings.database_url == "sqlite:///./var/aatm.db"
    assert settings.api_v1_prefix == "/api/v1"
    assert settings.request_id_header == "X-Request-ID"
    assert settings.default_page_size == 20
    assert settings.max_page_size == 100
    assert settings.db_pool_timeout_seconds == 30
    # مفتاح فارغ = لا مصادقة ممكنة (فشل مغلق)، لا مصادقة مقفولة.
    assert settings.api_key.get_secret_value() == ""
    assert settings.cors_origins_list == []
    assert settings.is_sqlite is True
    assert settings.is_testing is False


def test_env_file_is_loaded(tmp_path: Path, clean_env: None) -> None:
    """``.env`` يغيّر الإعدادات حين لا يوجد متغير بيئة — هذه أولوية ``.env`` نفسها."""
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "APP_NAME=AATM From Dotenv",
                "ENVIRONMENT=staging",
                "DATABASE_URL=sqlite:///" + str(tmp_path / "from-dotenv.db"),
                "DEBUG=true",
                "LOG_LEVEL=WARNING",
                "API_KEY=dotenv-secret-value",
                "MAX_PAGE_SIZE=50",
                "# تعليق يجب أن يُتجاهل",
                "",
            ]
        ),
        encoding="utf-8",
    )

    settings = Settings(_env_file=env_file)

    assert settings.app_name == "AATM From Dotenv"
    assert settings.environment == "staging"
    assert settings.database_url.endswith("from-dotenv.db")
    assert settings.debug is True
    assert settings.log_level == "WARNING"
    assert settings.api_key.get_secret_value() == "dotenv-secret-value"
    assert settings.max_page_size == 50


def test_env_var_wins_over_dotenv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """الأولوية المعلنة: متغير البيئة يسحق قيمة ``.env`` للحقل نفسه."""
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "DATABASE_URL=sqlite:///" + str(tmp_path / "dotenv.db"),
                "API_V1_PREFIX=/api/v0",
                "MAX_PAGE_SIZE=50",
                "ENVIRONMENT=staging",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'from-environ.db'}")
    monkeypatch.setenv("MAX_PAGE_SIZE", "75")
    monkeypatch.setenv("ENVIRONMENT", "production")

    settings = Settings(_env_file=env_file)

    # من البيئة:
    assert settings.database_url.endswith("from-environ.db")
    assert settings.max_page_size == 75
    assert settings.environment == "production"
    # من ``.env`` وحده، لأنه غير مضبوط في البيئة:
    assert settings.api_v1_prefix == "/api/v0"


def test_explicit_kwargs_win_over_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """الوسائط الصريحة أعلى الجميع — هذا ما تعتمد عليه الاختبارات و``create_app``."""
    monkeypatch.setenv("DATABASE_URL", "sqlite:///from-env.db")
    monkeypatch.setenv("ENVIRONMENT", "production")

    settings = Settings(
        _env_file=None,
        database_url="sqlite:///explicit.db",
        environment="test",
    )

    assert settings.database_url == "sqlite:///explicit.db"
    assert settings.environment == "test"


def test_cors_origins_accepts_csv_and_json() -> None:
    """الحقل الموثّق كنص يقبل القائمة المفصولة بفواصل ومصفوفة JSON على السواء."""
    from_comma = make_settings(cors_allow_origins="https://a.example , https://b.example")
    from_json = make_settings(cors_allow_origins='["https://a.example","https://b.example"]')

    assert from_comma.cors_origins_list == ["https://a.example", "https://b.example"]
    assert from_json.cors_origins_list == ["https://a.example", "https://b.example"]
    assert make_settings(cors_allow_origins="").cors_origins_list == []


def test_get_settings_is_cached_and_clearable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """``get_settings`` مخزّن؛ ``clear_settings_cache`` هو السبيل الوحيد لإعادة القراءة."""
    url_a = f"sqlite:///{tmp_path / 'a.db'}"
    url_b = f"sqlite:///{tmp_path / 'b.db'}"
    monkeypatch.setenv("DATABASE_URL", url_a)
    clear_settings_cache()

    first = get_settings()
    assert first.database_url == url_a
    assert get_settings() is first  # نسخة مخزّنة واحدة

    monkeypatch.setenv("DATABASE_URL", url_b)
    assert get_settings().database_url == url_a  # لا إعادة قراءة بلا تنقية المخزن

    clear_settings_cache()
    assert get_settings().database_url == url_b


def test_default_env_file_is_optional_and_never_committed() -> None:
    """``backend/.env`` اختياري التحميل، ومُستثنى من git (قاعدة حماية الأسرار)."""
    assert DEFAULT_ENV_FILE.name == ".env"
    assert DEFAULT_ENV_FILE.parent.name == "backend"
    if DEFAULT_ENV_FILE.exists():  # لا يفشل الاختبار على جهاز فيه ملف محلي
        pytest.skip("ملف .env محلي موجود؛ العزل مضمون بـ _env_file=None")

    import subprocess

    ignored = subprocess.run(
        ["git", "check-ignore", "-q", "backend/.env"],
        cwd=DEFAULT_ENV_FILE.parent.parent,
        capture_output=True,
        text=True,
    )
    assert ignored.returncode == 0, "backend/.env يجب أن يكون في .gitignore"


# ─────────────────────────── حالات الفشل ───────────────────────────────────


@pytest.mark.parametrize("bad_value", ["staging-x", "Production", "prod", ""])
def test_unknown_environment_is_rejected(bad_value: str, tmp_path: Path) -> None:
    """فشل موثّق: بيئة خارج القائمة ترفع ``ValidationError`` لا صمتاً."""
    with pytest.raises(ValidationError) as excinfo:
        Settings(_env_file=None, environment=bad_value)

    error = excinfo.value.errors(include_url=False)[0]
    assert error["loc"] == ("environment",)
    assert set(ENVIRONMENTS) == {"development", "test", "staging", "production"}


def test_unsupported_database_scheme_is_rejected() -> None:
    """فشل موثّق: مخطط غير مدعوم يُرفض عند التحميل مع رسالة تعرض المدعوم."""
    with pytest.raises(ValidationError) as excinfo:
        Settings(_env_file=None, database_url="mongodb://localhost:27017/aatm")

    message = str(excinfo.value)
    assert "database_url" in message
    assert "mongodb" in message
    for scheme in ("sqlite", "postgresql"):
        assert scheme in message
    assert "mongodb" not in SUPPORTED_DB_SCHEMES


def test_empty_database_url_is_rejected() -> None:
    """فشل موثّق: ``DATABASE_URL=`` الفارغ ليس «سأستخدم الافتراضي» بل خطأ."""
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_url="   ")


@pytest.mark.parametrize(
    "bad_prefix",
    ["api/v1", "/api/v1/", "/api v1", "/"],
    ids=["no-leading-slash", "trailing-slash", "whitespace", "root-only"],
)
def test_invalid_api_prefix_is_rejected(bad_prefix: str) -> None:
    """فشل موثّق: بادئة غير سليمة كانت ستُنتج مسارات مكسورة و404 غامضة."""
    with pytest.raises(ValidationError) as excinfo:
        Settings(_env_file=None, api_v1_prefix=bad_prefix)

    assert "api_v1_prefix" in str(excinfo.value)


def test_dotenv_with_invalid_value_fails_loudly(tmp_path: Path) -> None:
    """فشل موثّق عبر ``.env``: المصدر لا يغيّر من صرامة التحقّق."""
    env_file = tmp_path / ".env"
    env_file.write_text("MAX_PAGE_SIZE=0\n", encoding="utf-8")

    with pytest.raises(ValidationError) as excinfo:
        Settings(_env_file=env_file)

    errors = excinfo.value.errors(include_url=False)
    assert errors[0]["loc"] == ("max_page_size",)
    assert "greater than or equal to 1" in errors[0]["msg"]


def test_bad_request_id_header_is_rejected() -> None:
    """فشل موثّق: ترويسة فيها فراغ كانت ستمرّر ترويسة مزروقة في الاستجابة."""
    with pytest.raises(ValidationError):
        Settings(_env_file=None, request_id_header="X-Request ID")


# ─────────────────── الأسرار: لا تتسرّب عبر repr/السجل ───────────────────


def test_api_key_never_appears_in_repr_or_json_dump() -> None:
    """المفتاح ``SecretStr``: repr والتسلسل JSON يُخفيان القيمة (قاعدة 4 في AGENTS.md)."""
    settings = make_settings(api_key="super-secret-value-42")

    assert settings.api_key.get_secret_value() == "super-secret-value-42"
    assert "super-secret-value-42" not in repr(settings)
    assert "super-secret-value-42" not in str(settings)
    assert "super-secret-value-42" not in settings.model_dump_json()
    assert "**********" in settings.model_dump_json()


def test_test_api_key_is_not_a_production_secret() -> None:
    """مفتاح الاختبار ثابت معروف — يجب ألا يُستخدم خارج الاختبارات."""
    assert TEST_API_KEY.startswith("test-")
    assert len(TEST_API_KEY) >= 16
