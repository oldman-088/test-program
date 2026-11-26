"""Score submission endpoint tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

VALID = {
    "player_name": "ليلى",
    "difficulty": "medium",
    "attempts": 14,
    "duration_seconds": 95,
}


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"]


def test_create_score_returns_201_and_persists(client: TestClient) -> None:
    response = client.post("/api/v1/scores", json=VALID)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["id"] > 0
    assert body["player_name"] == "ليلى"
    assert body["difficulty"] == "medium"
    assert body["attempts"] == 14
    assert body["finished_at"].endswith("Z") or "+00:00" in body["finished_at"]

    board = client.get("/api/v1/leaderboard", params={"difficulty": "medium"}).json()
    assert board["total"] == 1
    assert board["entries"][0]["player_name"] == "ليلى"


def test_player_name_is_trimmed(client: TestClient) -> None:
    payload = {**VALID, "player_name": "  عمر  "}
    response = client.post("/api/v1/scores", json=payload)
    assert response.status_code == 201
    assert response.json()["player_name"] == "عمر"


def test_explicit_finished_at_is_honoured(client: TestClient) -> None:
    payload = {**VALID, "finished_at": "2026-11-01T10:30:00+02:00"}
    response = client.post("/api/v1/scores", json=payload)
    assert response.status_code == 201
    assert response.json()["finished_at"].startswith("2026-11-01T08:30:00")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("player_name", ""),
        ("player_name", "   "),
        ("player_name", "x" * 41),
        ("difficulty", "insane"),
        ("attempts", 0),
        ("attempts", -3),
        ("attempts", 10_001),
        ("duration_seconds", 0),
        ("duration_seconds", 86_401),
        ("attempts", "many"),
    ],
)
def test_invalid_payload_is_rejected(client: TestClient, field: str, value: object) -> None:
    response = client.post("/api/v1/scores", json={**VALID, field: value})
    assert response.status_code == 422
    assert field in response.text


@pytest.mark.parametrize("missing", list(VALID))
def test_missing_field_is_rejected(client: TestClient, missing: str) -> None:
    payload = {key: value for key, value in VALID.items() if key != missing}
    response = client.post("/api/v1/scores", json=payload)
    assert response.status_code == 422


def test_stats_summarises_games(client: TestClient) -> None:
    client.post("/api/v1/scores", json=VALID)
    client.post("/api/v1/scores", json={**VALID, "attempts": 9, "duration_seconds": 60})

    stats = client.get("/api/v1/stats").json()
    assert stats["medium"] == {"games": 2, "best_attempts": 9, "best_duration": 60}
    assert "easy" not in stats
