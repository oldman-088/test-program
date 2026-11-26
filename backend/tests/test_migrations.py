"""Migrations and schema tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text

from alembic import command
from alembic.config import Config
from app.config import get_settings
from tests.conftest import BACKEND_DIR, _alembic_config

EXPECTED_COLUMNS = {
    "id",
    "player_name",
    "difficulty",
    "attempts",
    "duration_seconds",
    "finished_at",
}


def test_head_revision_is_applied() -> None:
    engine = create_engine(get_settings().database_url)
    with engine.connect() as connection:
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert revision == "0001"

    inspector = inspect(engine)
    assert "scores" in inspector.get_table_names()
    columns = {column["name"] for column in inspector.get_columns("scores")}
    assert columns == EXPECTED_COLUMNS
    indexes = {index["name"] for index in inspector.get_indexes("scores")}
    assert {"ix_scores_difficulty_rank", "ix_scores_finished_at"} <= indexes


def test_migration_upgrade_downgrade_upgrade_on_fresh_database(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'fresh.db'}"
    cfg: Config = _alembic_config()
    cfg.set_main_option("sqlalchemy.url", url)

    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    get_settings.cache_clear()
    try:
        engine = create_engine(url)

        command.upgrade(cfg, "head")
        assert "scores" in inspect(engine).get_table_names()

        command.downgrade(cfg, "base")
        assert "scores" not in inspect(engine).get_table_names()

        command.upgrade(cfg, "head")
        assert "scores" in inspect(engine).get_table_names()
        engine.dispose()
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous
        get_settings.cache_clear()


def test_alembic_ini_lives_next_to_app() -> None:
    assert (BACKEND_DIR / "alembic.ini").is_file()


@pytest.mark.parametrize("revision", ["0001"])
def test_known_revisions_exist(revision: str) -> None:
    versions = BACKEND_DIR / "alembic" / "versions"
    assert any(path.stem.startswith(revision) for path in versions.glob("*.py"))
