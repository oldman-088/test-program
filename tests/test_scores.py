"""Tests for POST /api/v1/scores and the /health endpoint."""

from datetime import UTC, datetime

import pytest


def test_health_returns_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_valid_score_returns_201_with_id(client, valid_payload):
    response = client.post("/api/v1/scores", json=valid_payload)

    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["id"], int)
    assert body["id"] > 0
    assert body["player_name"] == "sara"
    assert body["difficulty"] == "easy"
    assert body["attempts"] == 4
    assert body["duration_seconds"] == 25.5
    assert body["finished_at"].startswith("2026-11-21T10:00:00")
    assert body["created_at"]


def test_create_score_defaults_finished_at_to_now(client, valid_payload):
    payload = {key: value for key, value in valid_payload.items() if key != "finished_at"}

    response = client.post("/api/v1/scores", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["finished_at"] is not None
    parsed = datetime.fromisoformat(body["finished_at"].replace("Z", "+00:00"))
    delta = datetime.now(UTC) - parsed.astimezone(UTC)
    assert abs(delta.total_seconds()) < 60


def test_player_name_is_stripped(client, valid_payload):
    payload = {**valid_payload, "player_name": "   omar   "}

    response = client.post("/api/v1/scores", json=payload)

    assert response.status_code == 201
    assert response.json()["player_name"] == "omar"


@pytest.mark.parametrize(
    "overrides",
    [
        {"player_name": "x" * 41},  # name longer than 40 chars
        {"player_name": ""},  # empty name
        {"player_name": "    "},  # whitespace-only name
        {"difficulty": "impossible"},  # unknown difficulty
        {"attempts": 0},  # attempts must be > 0
        {"attempts": -3},
        {"attempts": 10001},  # unreasonable attempt count
        {"duration_seconds": 0},  # duration must be > 0
        {"duration_seconds": -1.5},
        {"duration_seconds": 86401},  # longer than one day
        {"player_name": None},  # missing type
        {"attempts": "four"},  # wrong type
    ],
)
def test_invalid_score_is_rejected_with_422(client, valid_payload, overrides):
    payload = {**valid_payload, **overrides}

    response = client.post("/api/v1/scores", json=payload)

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert isinstance(detail, list) and len(detail) > 0


def test_missing_required_fields_is_rejected_with_422(client, valid_payload):
    for field in ("player_name", "difficulty", "attempts", "duration_seconds"):
        payload = {key: value for key, value in valid_payload.items() if key != field}

        response = client.post("/api/v1/scores", json=payload)

        assert response.status_code == 422, f"expected 422 when {field} is missing"


def test_finished_at_with_timezone_offset_is_normalized_to_utc(client, valid_payload):
    """12:00+02:00 must be stored and returned as 10:00Z, not wall time."""
    payload = {**valid_payload, "finished_at": "2026-11-21T12:00:00+02:00"}

    response = client.post("/api/v1/scores", json=payload)

    assert response.status_code == 201
    assert response.json()["finished_at"] == "2026-11-21T10:00:00Z"


def test_naive_finished_at_is_treated_as_utc(client, valid_payload):
    """SQLite returns datetimes naive; the API must still answer with Z."""
    payload = {**valid_payload, "finished_at": "2026-11-21T10:00:00"}

    response = client.post("/api/v1/scores", json=payload)

    assert response.status_code == 201
    assert response.json()["finished_at"] == "2026-11-21T10:00:00Z"


def test_response_datetimes_always_carry_utc_suffix(client, valid_payload):
    """finished_at/created_at must be UTC-aware in every response."""
    response = client.post("/api/v1/scores", json=valid_payload)

    assert response.status_code == 201
    body = response.json()
    assert body["finished_at"].endswith("Z")
    assert body["created_at"].endswith("Z")

    leaderboard = client.get("/api/v1/leaderboard").json()
    assert leaderboard[0]["finished_at"].endswith("Z")
