"""Health endpoints: process liveness and database connectivity.

Both routes are deliberately public (no authentication): orchestrators, load
balancers and CI must reach them without credentials.
"""

from __future__ import annotations

import logging
import socket
import sqlite3
from dataclasses import dataclass
from typing import Annotated, Literal
from urllib.parse import unquote, urlparse

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.core.errors import ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

# TCP ports used when the DATABASE_URL does not carry an explicit port.
_DEFAULT_PORTS: dict[str, int] = {
    "postgresql": 5432,
    "postgres": 5432,
    "mysql": 3306,
    "mariadb": 3306,
    "mssql": 1433,
    "mongodb": 27017,
    "mongodb+srv": 27017,
    "redis": 6379,
}


class HealthResponse(BaseModel):
    """Liveness payload: identity of the running process."""

    status: Literal["ok"]
    app: str
    version: str
    environment: Literal["development", "test", "staging", "production"]


class HealthDBResponse(BaseModel):
    """Database connectivity payload. Never contains credentials."""

    status: Literal["ok"]
    database: str
    dialect: str


@dataclass(frozen=True)
class DatabaseTarget:
    """Parsed view of ``DATABASE_URL`` (credentials are never kept or exposed)."""

    dialect: str
    database: str
    sqlite_path: str | None = None
    host: str | None = None
    port: int | None = None


def parse_database_url(database_url: str) -> DatabaseTarget:
    """Parse a SQLAlchemy-style URL into a probe target without storing credentials."""
    parsed = urlparse(database_url.strip())
    dialect = parsed.scheme.lower() or "unknown"
    if dialect == "sqlite":
        raw = parsed.path or ""
        # SQLAlchemy convention: "sqlite:///relative.db" yields path "/relative.db"
        # (a relative file), while "sqlite:////abs/db" yields "//abs/db" (absolute).
        # Strip exactly one leading slash; keep ":memory:" as-is.
        sqlite_path = raw[1:] if raw.startswith("/") else raw
        database = sqlite_path.rsplit("/", 1)[-1] if sqlite_path else ":memory:"
        return DatabaseTarget(
            dialect=dialect,
            database=database or ":memory:",
            sqlite_path=sqlite_path or None,
        )
    database = unquote(parsed.path.lstrip("/").rsplit("/", 1)[-1]) if parsed.path else ""
    port = parsed.port
    if port is None:
        port = _DEFAULT_PORTS.get(dialect)
    return DatabaseTarget(dialect=dialect, database=database or "unknown", host=parsed.hostname, port=port)


def _probe_database(target: DatabaseTarget) -> None:
    """Verify connectivity; raise an exception when the database cannot be reached.

    * sqlite: opens the file (creating it when missing, as our default dev database
      is created lazily) and executes ``SELECT 1``.
    * network databases: opens a TCP connection to host:port.
    * unknown dialects without a host cannot be probed; connectivity is then
      reported as unverified but assumed fine (documented in docs/API.md).
    """
    if target.dialect == "sqlite":
        connection = sqlite3.connect(target.sqlite_path or ":memory:", timeout=2)
        try:
            connection.execute("SELECT 1")
        finally:
            connection.close()
        return
    if target.host:
        with socket.create_connection((target.host, target.port or 0), timeout=2):
            return
    logger.info(
        "Database connectivity not verifiable for dialect %r; skipping probe",
        target.dialect,
        extra={"dialect": target.dialect},
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness probe",
    description="Returns process identity: status, app name, version and environment.",
)
async def read_health(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )


@router.get(
    "/health/db",
    response_model=HealthDBResponse,
    responses={
        503: {
            "model": ErrorResponse,
            "description": "Database unreachable (unified error template, code `database_unreachable`).",
        }
    },
    summary="Database connectivity probe",
    description="Checks the configured DATABASE_URL and reports status, database name and dialect.",
)
async def read_health_db(settings: Annotated[Settings, Depends(get_settings)]) -> HealthDBResponse:
    target = parse_database_url(settings.database_url)
    try:
        _probe_database(target)
    except Exception as exc:  # noqa: BLE001 - any failure means "unreachable"
        logger.warning(
            "Database health check failed",
            extra={"dialect": target.dialect, "database": target.database, "error_type": type(exc).__name__},
        )
        raise HTTPException(
            status_code=503,
            detail={
                "code": "database_unreachable",
                "message": "Database is unreachable.",
                "details": {
                    "dialect": target.dialect,
                    "database": target.database,
                    "error_type": type(exc).__name__,
                },
            },
        ) from exc
    return HealthDBResponse(status="ok", database=target.database, dialect=target.dialect)
