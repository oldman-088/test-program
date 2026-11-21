"""Game scores service configuration.

All settings come from environment variables (or a local ``.env`` file) so the
service can be reconfigured without touching code.
"""

import json
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _normalize_database_url(url: str) -> str:
    """Accept legacy ``postgres://`` URLs and map them to a SQLAlchemy driver."""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


def _parse_origins(value: str) -> list[str]:
    """Parse a CORS origins string: comma-separated, or a JSON array.

    Comma-separated is the documented format (``CORS_ORIGINS=a,b``); a JSON
    array string (``CORS_ORIGINS='["a","b"]'``) is accepted as well.
    """
    text_value = value.strip()
    if text_value.startswith("["):
        try:
            parsed = json.loads(text_value)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list):
            return [str(origin).strip() for origin in parsed if str(origin).strip()]
    return [origin.strip() for origin in text_value.split(",") if origin.strip()]


class Settings(BaseSettings):
    """Service settings, overridable through environment variables."""

    # SQLite by default; point DATABASE_URL at PostgreSQL to switch stores.
    database_url: str = "sqlite:///./scores.db"

    # Comma-separated list of allowed browser origins (JSON array also
    # accepted). Restricted to the Vite dev server by default and configurable
    # via CORS_ORIGINS. NoDecode stops pydantic-settings from json.loads-ing
    # the raw env string, which would crash startup on the comma format; the
    # string is parsed by _split_cors_origins instead.
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def _clean_database_url(cls, value: str) -> str:
        return _normalize_database_url(value.strip())

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value):
        if isinstance(value, str):
            return _parse_origins(value)
        return value


settings = Settings()
