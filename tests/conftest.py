"""Shared pytest fixtures.

Every test gets a fresh SQLite database in a temporary directory, created by
running the real Alembic migrations from scratch (``alembic upgrade head``).
The app's ``get_db`` dependency is overridden so all requests hit that database.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from alembic import command

BASE_DIR = Path(__file__).resolve().parent.parent


def _run_migrations(database_url: str) -> None:
    """Apply all Alembic migrations to ``database_url`` from scratch."""
    alembic_cfg = Config(str(BASE_DIR / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(BASE_DIR / "alembic"))
    alembic_cfg.attributes["database_url"] = database_url
    command.upgrade(alembic_cfg, "head")


@pytest.fixture()
def db_session(tmp_path: Path) -> Iterator[Session]:
    """A session bound to a freshly migrated per-test SQLite database."""
    database_url = f"sqlite:///{tmp_path / 'scores.db'}"
    _run_migrations(database_url)

    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client(db_session: Session) -> Iterator[TestClient]:
    """TestClient wired to the per-test database via dependency override."""
    from app.database import get_db
    from app.main import app

    def override_get_db() -> Iterator[Session]:
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def valid_payload() -> dict:
    """A minimal valid score submission payload."""
    return {
        "player_name": "sara",
        "difficulty": "easy",
        "attempts": 4,
        "duration_seconds": 25.5,
        "finished_at": "2026-11-21T10:00:00Z",
    }
