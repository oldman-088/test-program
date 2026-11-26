"""بيئة Alembic — مصدر سلسلة الاتصال واحد مثل التطبيق تماماً.

الأولوية (مُختبَرة في ``backend/tests/test_database.py``):
    1. ``sqlalchemy.url`` المضبوطة في ملف/كائن الإعداد (طريقة الاختبارات).
    2. ``alembic -x url=sqlite:////tmp/x.db``.
    3. متغير البيئة ``DATABASE_URL``.
    4. ``Settings.database_url`` (متغيرات البيئة ثم ``backend/.env`` ثم الافتراضي).
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import Settings  # noqa: E402
from app.core.database import Base  # noqa: E402
from app.models import AgentSession  # noqa: E402,F401  (تسجيل النموذج في metadata)

config = context.config
if config.config_file_name is not None:
    # ``disable_existing_loggers=False`` إلزامي: وإلا عطّل كل مسجّل قائم — بمن فيهم
    # ``app.errors`` — فتصمت سجلّات التطبيق بعد أول هجرة في نفس العملية (يمسكه
    # ``tests/test_errors.py::test_unhandled_exception_is_logged_but_never_leaked``).
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def _extra_url() -> str | None:
    """يسمح لـ ``alembic -x url=sqlite:////tmp/x.db`` باستهداف قاعدة أخرى."""
    x_args = context.get_x_argument(as_dictionary=True)
    url = x_args.get("url")
    return url or None


def resolve_url() -> str:
    url = (
        config.get_main_option("sqlalchemy.url")
        or _extra_url()
        or os.environ.get("DATABASE_URL")
        or Settings().database_url
    )
    return str(url)


def configure() -> None:
    """يكتب السلسلة النهائية في الإعداد، فيراها ``offline`` و``online`` معاً."""
    if not config.get_main_option("sqlalchemy.url"):
        config.set_main_option("sqlalchemy.url", resolve_url())


def run_migrations_offline() -> None:
    url = resolve_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        render_as_batch=url.startswith("sqlite"),
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = resolve_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            # SQLite لا يدعم ALTER الكامل؛ الدفعات ضرورية لتمرير هجرات لاحقة عليه.
            render_as_batch=connection.dialect.name == "sqlite",
        )
        with context.begin_transaction():
            context.run_migrations()


configure()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
