"""Game scores service configuration.

All settings come from environment variables (or a local ``.env`` file) so the
service can be reconfigured without touching code.
"""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _normalize_database_url(url: str) -> str:
    """Accept legacy ``postgres://`` URLs and map them to a SQLAlchemy driver."""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


class Settings(BaseSettings):
    """Service settings, overridable through environment variables."""

    # SQLite by default; point DATABASE_URL at PostgreSQL to switch stores.
    database_url: str = "sqlite:///./scores.db"

    # Comma-separated list of allowed browser origins. Restricted to the Vite
    # dev server by default and configurable via CORS_ORIGINS.
    cors_origins: list[str] = ["http://localhost:5173"]

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
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


settings = Settings()
