"""Tests for the CORS configuration (allowed origin configurable via env)."""

ALLOWED_ORIGIN = "http://localhost:5173"


def test_cors_preflight_allows_configured_origin(client):
    response = client.options(
        "/api/v1/scores",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert "POST" in response.headers["access-control-allow-methods"]


def test_cors_preflight_rejects_unknown_origin(client):
    response = client.options(
        "/api/v1/scores",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert "access-control-allow-origin" not in response.headers


def test_cors_simple_request_gets_allow_origin_header(client):
    response = client.get("/health", headers={"Origin": ALLOWED_ORIGIN})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN


def test_cors_origins_default_comes_from_settings():
    """The default allow-list must come from configuration, not hardcoded code."""
    from app.config import Settings

    default_settings = Settings(_env_file=None)
    assert default_settings.cors_origins == [ALLOWED_ORIGIN]

    overridden = Settings(_env_file=None, cors_origins="http://localhost:3000, http://localhost:5173")
    assert overridden.cors_origins == ["http://localhost:3000", ALLOWED_ORIGIN]
