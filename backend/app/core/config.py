"""إعدادات طبقة الخلفية — البند 21 · المهمة AATM-984687b7 · دُمجت حقول AATM-49a40f0c.

مسؤولية هذا الملف: تعريف مصدر وحيد للإعدادات يقرأ (بترتيب أولوية مُختبَر):

    1. القيم الممرّرة صراحةً عند البناء (``Settings(DATABASE_URL=...)``) — للأدوات والاختبارات.
    2. متغيرات البيئة ``os.environ``.
    3. ملف ``.env`` (جذر المستودع ثم ``backend/.env`` كتجاوز محلي) إن وُجد — لا يُعمَّد أبداً.
    4. القيم الافتراضية الواردة أدناه.

التشغيل لا يتطلّب أي سرّ إلزامي ولا اتصال شبكة: كل حقل له قيمة افتراضية عاملة،
و``SECRET_KEY`` اختياري (``.env.example`` يوثّق البدائل فقط).

لا يقرأ هذا الملف أي شبكة ولا يتصل بأي خدمة.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, ClassVar, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

#: مجلد ``backend/`` — مرجع كل المسارات النسبية، حتى يعمل الاستدعاء من أي cwd.
BACKEND_DIR: Path = Path(__file__).resolve().parents[2]

#: جذر المستودع — يُقرأ منه ``.env`` (مكانه الموثّق في ``.env.example``).
REPO_ROOT: Path = BACKEND_DIR.parent

#: ملف البيئة المحلي. اختياري تماماً؛ غيابه ليس خطأ.
DEFAULT_ENV_FILE: Path = BACKEND_DIR / ".env"

#: البيئات المسموحة. أي قيمة أخرى مرفوضة عند التحميل (لا بيئات مجهولة في الإنتاج).
ENVIRONMENTS: tuple[str, ...] = ("development", "test", "staging", "production")

#: المخططات المسموح بها في ``DATABASE_URL``. SQLite للتطوير/الاختبار و Postgres للتشغيل.
SUPPORTED_DB_SCHEMES: tuple[str, ...] = (
    "sqlite",
    "sqlite+aiosqlite",
    "postgresql",
    "postgresql+psycopg",
    "postgresql+psycopg2",
    "postgresql+asyncpg",
)


class Settings(BaseSettings):
    """الحقل ↔ متغير البيئة: اسم الحقل بحروف كبيرة (``database_url`` ↔ ``DATABASE_URL``)."""

    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", DEFAULT_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    #: القيم الافتراضية التي يوثّقها ``docs/API.md`` وتتحقق منها الاختبارات.
    DEFAULT_APP_NAME: ClassVar[str] = "AATM Backend"
    DEFAULT_DATABASE_URL: ClassVar[str] = "sqlite:///./var/aatm.db"
    DEFAULT_API_PREFIX: ClassVar[str] = "/api/v1"
    DEFAULT_PAGE_SIZE: ClassVar[int] = 20

    app_name: str = DEFAULT_APP_NAME
    #: إصدار العملية الذي يُعاد في ``GET /api/health`` (AATM-49a40f0c).
    app_version: str = "0.1.0"
    environment: Literal["development", "test", "staging", "production"] = "development"
    debug: bool = False
    log_level: Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"] = "INFO"

    database_url: str = DEFAULT_DATABASE_URL
    #: مهلة احتجاز سجلّ واحد (مهام/جلسات) بالثواني.
    db_pool_timeout_seconds: int = Field(default=30, ge=1, le=600)
    #: أقصى عدد صفوف تُرجعها نقاط القائمة.
    default_page_size: int = Field(default=DEFAULT_PAGE_SIZE, ge=1, le=200)
    max_page_size: int = Field(default=100, ge=1, le=1000)

    api_v1_prefix: str = DEFAULT_API_PREFIX
    request_id_header: str = "X-Request-ID"
    #: مفتاح API بسيط لحماية نقاط العمل (Q5). فارغ = الحماية مُفعّلة وكل الطلبات مرفوضة.
    api_key: SecretStr = SecretStr("")
    #: سرّ اختياري لتوقيع الجلسات في مراحل لاحقة — الإقلاع لا يحتاجه أبداً.
    secret_key: str | None = None
    #: قائمة origins مفصولة بفواصل أو مصفوفة JSON (كلاهما مقبول).
    cors_allow_origins: str = ""
    #: origins واجهة اللوحة (AATM-49a40f0c) — مفصولة بفواصل، تُضاف إلى قائمة CORS.
    frontend_origin: str = "http://localhost:5173"

    @field_validator("database_url")
    @classmethod
    def _validate_database_url(cls, value: str) -> str:
        """يرفض أي مخطط غير مدعوم بدل أن ينفجر عند أول اتصال."""
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("database_url must not be empty")
        scheme = cleaned.split("://", 1)[0].lower() if "://" in cleaned else ""
        if scheme not in SUPPORTED_DB_SCHEMES:
            allowed = ", ".join(sorted(SUPPORTED_DB_SCHEMES))
            raise ValueError(f"database_url scheme {scheme!r} is unsupported; expected one of: {allowed}")
        return cleaned

    @field_validator("api_v1_prefix")
    @classmethod
    def _validate_prefix(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned.startswith("/"):
            raise ValueError("api_v1_prefix must start with '/'")
        if cleaned.endswith("/"):
            raise ValueError("api_v1_prefix must not end with '/'")
        if any(ch.isspace() for ch in cleaned):
            raise ValueError("api_v1_prefix must not contain whitespace")
        return cleaned

    @field_validator("request_id_header")
    @classmethod
    def _validate_header_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned or any(ch.isspace() for ch in cleaned):
            raise ValueError("request_id_header must be a single non-empty token")
        return cleaned

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def _accept_json_or_csv(cls, value: Any) -> str:
        """يسمح بـ ``["a","b"]`` أو ``a,b`` في ``.env`` — والتخزين دائماً نص."""
        if isinstance(value, (list, tuple, set)):
            return ",".join(str(item).strip() for item in value)
        if isinstance(value, str) and value.strip().startswith("["):
            import json

            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                return value
            if isinstance(parsed, list):
                return ",".join(str(item).strip() for item in parsed)
        return value

    @property
    def cors_origins_list(self) -> list[str]:
        return [item.strip() for item in self.cors_allow_origins.split(",") if item.strip()]

    @property
    def frontend_origins(self) -> list[str]:
        """``FRONTEND_ORIGIN`` كقائمة (origin واحد لكل إصدار من أجهزة اللوحة)."""
        return [origin.strip() for origin in self.frontend_origin.split(",") if origin.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def is_testing(self) -> bool:
        return self.environment == "test"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """نسخة مُخزّنة من الإعدادات للتشغيل العادي. الاختبارات تبني ``Settings`` خاصة بها."""
    return Settings()


def clear_settings_cache() -> None:
    """يُستدعى بعد تغيير متغيرات البيئة في الاختبارات/الأدوات."""
    get_settings.cache_clear()
