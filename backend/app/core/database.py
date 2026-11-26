"""طبقة قاعدة البيانات — البند 21 · المهمة AATM-984687b7.

تصميم مقصود ليكون قابلاً للعزل في الاختبارات:
* لا محرك على مستوى الوحدة (لا ``engine = create_engine(...)`` عند الاستيراد)؛
  كل ``Database`` يملك محركه، والاختبار يبني واحداً على ملف SQLite مؤقت.
* ``Base.metadata`` يحمل اتفاقيات تسمية صريحة، حتى ينتج Alembic تنازلاً (downgrade) نظيفاً.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import MetaData, create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import Settings, get_settings

#: اتفاقيات تسمية مطلوبة كي يستطيع Alembic حذف/إعادة إنشاء القيود في ``downgrade``.
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """الأب الوصفي لكل النماذج؛ ``metadata`` هو مرجع توليد الهجرات."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class DatabaseUnavailableError(SQLAlchemyError):
    """يرتفع عند فشل فحص الاتصال — تُترجمه معالجات الأخطاء إلى 503."""


class Database:
    """حامل محرك + مصنع جلسات لمخطط واحد."""

    def __init__(self, url: str, *, echo: bool = False, pool_timeout: int | None = None) -> None:
        kwargs: dict[str, Any] = {"echo": echo, "future": True}
        if url.startswith("sqlite"):
            # الاختبارات/TestClient تستخدم خيطاً واحداً، لكن uvicorn لا يضمن ذلك.
            kwargs["connect_args"] = {"check_same_thread": False}
            if ":memory:" in url:
                from sqlalchemy.pool import StaticPool

                kwargs["poolclass"] = StaticPool
        else:
            if pool_timeout is not None:
                kwargs["pool_timeout"] = pool_timeout
            kwargs["pool_pre_ping"] = True
        self.url = url
        self.engine: Engine = create_engine(url, **kwargs)
        self.sessionmaker = sessionmaker(bind=self.engine, autoflush=False, expire_on_commit=False)

    # ── المخطط ────────────────────────────────────────────────────────────
    def create_all(self) -> None:
        """إنشاء كل الجداول المعرفة في النماذج (للقواعد المؤقتة والاختبارات فقط)."""
        import app.models  # noqa: F401  # تسجيل كل النماذج قبل الإنشاء

        Base.metadata.create_all(self.engine)

    def drop_all(self) -> None:
        import app.models  # noqa: F401

        Base.metadata.drop_all(self.engine)

    def table_names(self) -> list[str]:
        return sorted(inspect(self.engine).get_table_names())

    def column_names(self, table: str) -> list[str]:
        insp = inspect(self.engine)
        if table not in insp.get_table_names():
            return []
        return [col["name"] for col in insp.get_columns(table)]

    # ── الجلسات ───────────────────────────────────────────────────────────
    @contextmanager
    def session(self) -> Iterator[Session]:
        """``commit`` عند النجاح و``rollback`` عند أي استثناء، وإغلاق دائماً."""
        session = self.sessionmaker()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # ── الفحص ─────────────────────────────────────────────────────────────
    def ping(self) -> bool:
        """استعلام ``SELECT 1`` حيّ. يرفع بدل أن يكذب عند انقطاع الاتصال."""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except SQLAlchemyError as exc:  # pragma: no cover - مسار نادر
            raise DatabaseUnavailableError(str(exc)) from exc
        return True

    def dispose(self) -> None:
        """يغلق كل اتصالات التجمع — تُنادى في ``shutdown`` ومن تثبيتات الاختبار."""
        self.engine.dispose()


# ── ربط سريع بـ FastAPI ──────────────────────────────────────────────────
def get_database(request: Any) -> Database:
    """يقرأ ``Database`` من ``app.state`` — لا حالة عامة على مستوى الوحدة."""
    return request.app.state.database


def build_database(settings: Settings | None = None) -> Database:
    """يبني ``Database`` من الإعدادات (يُستخدم في ``create_app`` وفي السكربتات)."""
    settings = settings or get_settings()
    return Database(
        settings.database_url,
        echo=settings.debug,
        pool_timeout=settings.db_pool_timeout_seconds,
    )
