"""Tests for the health routes, the unified error template, CORS and settings loading.

Reconciliation with the platform structure on ``main`` (review round 3): the served
error envelope is the platform-wide template of ``docs/API.md`` §2 (``code`` /
``message`` / ``details`` / ``request_id``) and the settings defaults are the documented
platform defaults of ``backend/app/core/config.py``; the assertions below were aligned to
those contracts while keeping every scenario of the original suite.

Run from ``backend/``: ``python -m pytest``.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api import health as health_module
from app.core.config import Settings
from app.main import create_app


@pytest.fixture(autouse=True)
def pure_settings_env(clean_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """Assert pure code defaults: no ambient settings variables leak into these tests.

    ``clean_env`` (``conftest.py``) strips the platform settings variables; the extra
    names below belong to the AATM-49a40f0c fields merged into ``Settings``.
    """
    for name in ("APP_VERSION", "SECRET_KEY", "FRONTEND_ORIGIN"):
        monkeypatch.delenv(name, raising=False)


def make_client(settings: Settings | None = None, **client_kwargs) -> TestClient:
    return TestClient(create_app(settings or Settings()), **client_kwargs)


# ---------------------------------------------------------------------------
# GET /api/health
# ---------------------------------------------------------------------------


def test_health_returns_identity_fields():
    settings = Settings(app_name="Test API", app_version="9.9.9", debug=True)
    response = make_client(settings).get("/api/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "app": "Test API",
        "version": "9.9.9",
        "environment": "development",
    }


def test_health_environment_is_production_when_debug_disabled():
    response = make_client(Settings(environment="production", debug=False)).get("/api/health")
    assert response.status_code == 200
    assert response.json()["environment"] == "production"


# ---------------------------------------------------------------------------
# GET /api/health/db
# ---------------------------------------------------------------------------


def test_health_db_reports_status_database_and_dialect():
    response = make_client(Settings(database_url="sqlite:///./nexus.db")).get("/api/health/db")
    assert response.status_code == 200
    body = response.json()
    assert body == {"status": "ok", "database": "nexus.db", "dialect": "sqlite"}


def test_health_db_never_exposes_credentials():
    response = make_client(Settings(database_url="postgresql://db_user:db_pass@example.test:5432/aatm")).get(
        "/api/health/db"
    )
    assert response.status_code == 503  # example.test:5432 is not reachable in tests
    text = response.text
    assert "db_user" not in text and "db_pass" not in text


def test_db_unreachable_uses_error_template(monkeypatch):
    def failing_probe(target):
        raise OSError("cannot connect")

    monkeypatch.setattr(health_module, "_probe_database", failing_probe)
    response = make_client(Settings(database_url="postgresql://db/dbname")).get("/api/health/db")
    assert response.status_code == 503
    error = response.json()["error"]
    assert error["code"] == "database_unreachable"
    assert error["details"] == {"dialect": "postgresql", "database": "dbname", "error_type": "OSError"}


# ---------------------------------------------------------------------------
# Contract: everything under /api, unified error template
# ---------------------------------------------------------------------------


def test_all_routes_are_mounted_under_api():
    client = make_client()
    assert client.get("/health").status_code == 404  # nothing served outside /api
    openapi = client.get("/api/openapi.json")
    assert openapi.status_code == 200
    assert "/api/health" in openapi.json()["paths"]
    assert "/api/health/db" in openapi.json()["paths"]


def test_unknown_route_uses_error_template():
    response = make_client().get("/api/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert set(body.keys()) == {"error"}
    error = body["error"]
    assert error["code"] == "not_found"
    assert isinstance(error["message"], str) and error["message"]
    assert error["details"] == []


def test_method_not_allowed_uses_error_template():
    response = make_client().post("/api/health", json={})
    assert response.status_code == 405
    error = response.json()["error"]
    assert error["code"] == "method_not_allowed"
    assert set(error.keys()) == {"code", "message", "details", "request_id"}


def test_validation_errors_use_unified_template():
    app = create_app(Settings())

    @app.get("/api/_validation-probe")
    async def probe(number: int) -> dict[str, int]:
        return {"number": number}

    response = TestClient(app).get("/api/_validation-probe", params={"number": "not-a-number"})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert isinstance(error["details"], list) and error["details"]
    assert set(error["details"][0].keys()) == {"field", "loc", "message", "type"}


def test_unhandled_exception_returns_internal_error_without_leaking_internals():
    app = create_app(Settings())

    @app.get("/api/_boom")
    async def boom() -> dict[str, str]:
        raise RuntimeError("secret internals must not leak")

    response = TestClient(app, raise_server_exceptions=False).get("/api/_boom")
    assert response.status_code == 500
    error = response.json()["error"]
    assert error["code"] == "internal_error"
    assert error["details"] == []
    assert "secret internals" not in response.text


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------


def test_cors_preflight_allows_frontend_origin():
    settings = Settings(frontend_origin="http://localhost:5173,https://dashboard.example.com")
    response = make_client(settings).options(
        "/api/health",
        headers={
            "Origin": "https://dashboard.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://dashboard.example.com"


# ---------------------------------------------------------------------------
# Settings (pydantic-settings, .env support, safe defaults)
# ---------------------------------------------------------------------------


def test_settings_have_safe_defaults_without_env_file():
    # ``_env_file=None`` disables .env loading so the test asserts the code defaults
    # even when a root ``.env`` exists (e.g. generated by scripts/setup.sh).
    settings = Settings(_env_file=None)
    assert settings.database_url == "sqlite:///./var/aatm.db"
    assert settings.app_name == "AATM Backend"
    assert settings.app_version == "0.1.0"
    assert settings.log_level == "INFO"
    assert settings.debug is False
    assert settings.secret_key is None  # optional: boot never requires a secret
    assert settings.frontend_origins == ["http://localhost:5173"]
    assert settings.environment == "development"


def test_settings_read_env_file(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("APP_NAME=Env API\nLOG_LEVEL=DEBUG\nDEBUG=true\n", encoding="utf-8")
    settings = Settings(_env_file=env_file)
    assert settings.app_name == "Env API"
    assert settings.log_level == "DEBUG"
    assert settings.environment == "development"
