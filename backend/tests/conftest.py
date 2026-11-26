"""Shared fixtures: temp SQLite DB, real Alembic migrations, FastAPI test client."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent

# Configure the app *before* importing anything that builds the engine.
TMP_DIR = Path(tempfile.mkdtemp(prefix="scores-tests-"))
DB_PATH = TMP_DIR / "test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["CORS_ORIGINS"] = "http://localhost:5173,http://127.0.0.1:5173"
os.environ["AUTO_CREATE_SCHEMA"] = "false"

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import delete  # noqa: E402

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from app.config import Settings  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import Score  # noqa: E402


def _alembic_config() -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    return cfg


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> Iterator[Path]:
    """Bring a brand-new temp database to head once per test session."""
    command.upgrade(_alembic_config(), "head")
    yield DB_PATH


@pytest.fixture(autouse=True)
def clean_scores() -> Iterator[None]:
    with SessionLocal() as session:
        session.execute(delete(Score))
        session.commit()
    yield
    with SessionLocal() as session:
        session.execute(delete(Score))
        session.commit()


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as test_client:
        yield test_client
