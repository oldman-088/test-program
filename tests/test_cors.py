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


def test_cors_origins_default_comes_from_settings(monkeypatch):
    """The default allow-list must come from configuration, not hardcoded code."""
    from app.config import Settings

    monkeypatch.delenv("CORS_ORIGINS", raising=False)

    default_settings = Settings(_env_file=None)
    assert default_settings.cors_origins == [ALLOWED_ORIGIN]

    overridden = Settings(_env_file=None, cors_origins="http://localhost:3000, http://localhost:5173")
    assert overridden.cors_origins == ["http://localhost:3000", ALLOWED_ORIGIN]


def test_cors_origins_comma_separated_env_value_is_parsed(monkeypatch):
    """Regression: a comma-separated CORS_ORIGINS env value must parse.

    pydantic-settings treats ``list[str]`` fields as complex values and tries
    ``json.loads`` on the raw env string before field validators run, which
    crashed startup with ``SettingsError`` on the documented comma format.
    The ``NoDecode`` annotation hands the raw string to our validator instead.
    """
    from app.config import Settings

    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")

    parsed = Settings(_env_file=None)

    assert parsed.cors_origins == [ALLOWED_ORIGIN, "http://localhost:3000"]


def test_cors_origins_env_value_ignores_spaces_and_empty_segments(monkeypatch):
    from app.config import Settings

    monkeypatch.setenv("CORS_ORIGINS", " http://localhost:5173 , http://localhost:3000 , ")

    parsed = Settings(_env_file=None)

    assert parsed.cors_origins == [ALLOWED_ORIGIN, "http://localhost:3000"]


def test_cors_origins_json_array_env_value_is_accepted(monkeypatch):
    """pydantic-settings' native JSON format stays supported alongside commas."""
    from app.config import Settings

    monkeypatch.setenv("CORS_ORIGINS", '["http://localhost:5173", "http://localhost:3000"]')

    parsed = Settings(_env_file=None)

    assert parsed.cors_origins == [ALLOWED_ORIGIN, "http://localhost:3000"]


def test_cors_origins_dotenv_value_is_parsed(tmp_path, monkeypatch):
    """The documented `cp .env.example .env` flow must boot (DotEnv source)."""
    from app.config import Settings

    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATABASE_URL=sqlite:///./scores.db\n"
        "CORS_ORIGINS=http://localhost:5173,http://localhost:3000\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("CORS_ORIGINS", raising=False)

    parsed = Settings(_env_file=env_file)

    assert parsed.cors_origins == [ALLOWED_ORIGIN, "http://localhost:3000"]
