"""CORS configuration tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

ALLOWED = "http://localhost:5173"


def test_preflight_from_allowed_origin(client: TestClient) -> None:
    response = client.options(
        "/api/v1/scores",
        headers={
            "Origin": ALLOWED,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED
    assert "POST" in response.headers["access-control-allow-methods"]


def test_simple_request_gets_cors_header(client: TestClient) -> None:
    response = client.get("/api/v1/leaderboard", headers={"Origin": ALLOWED})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED


def test_disallowed_origin_is_not_echoed(client: TestClient) -> None:
    response = client.options(
        "/api/v1/scores",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_preview_origins_are_accepted(client: TestClient) -> None:
    """Starlette's TestClient host should not block same-origin browser traffic."""
    response = client.post(
        "/api/v1/scores",
        json={"player_name": "p", "difficulty": "easy", "attempts": 5, "duration_seconds": 30},
    )
    assert response.status_code == 201
