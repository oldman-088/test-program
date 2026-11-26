"""Application settings loaded from the environment (and optional ``.env`` files) via pydantic-settings.

Precedence (highest first), following pydantic-settings defaults:

1. Real environment variables.
2. ``.env`` files, loaded in the order below (later files win):
   - ``<repo root>/.env`` (the canonical location; see ``.env.example`` at the repo root),
   - ``backend/.env`` (optional local override when running from ``backend/``).
3. Field defaults declared here.

Boot must never require a mandatory secret or network connection: every field has a
working default and ``SECRET_KEY`` is optional.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> parents[2] is backend/, parents[3] is the repo root.
BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Environment-driven settings with safe defaults (no secrets required)."""

    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = "sqlite:///./nexus.db"
    frontend_origin: str = "http://localhost:5173"
    log_level: str = "INFO"
    app_name: str = "AATM API"
    app_version: str = "0.1.0"
    debug: bool = False
    secret_key: str | None = None  # Optional; needed only for signed tokens/sessions later.

    @property
    def frontend_origins(self) -> list[str]:
        """Comma-separated ``FRONTEND_ORIGIN`` entries as a list (e.g. one origin per deployment)."""
        return [origin.strip() for origin in self.frontend_origin.split(",") if origin.strip()]

    @property
    def environment(self) -> str:
        """Environment label derived from ``DEBUG``: ``development`` when debugging, else ``production``."""
        return "development" if self.debug else "production"


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor used across the app."""
    return Settings()
