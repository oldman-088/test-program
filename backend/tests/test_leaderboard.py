"""Leaderboard ordering, filtering and validation tests."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient


def post(client: TestClient, **overrides: Any) -> None:
    payload = {
        "player_name": "player",
        "difficulty": "easy",
        "attempts": 10,
        "duration_seconds": 60,
        **overrides,
    }
    response = client.post("/api/v1/scores", json=payload)
    assert response.status_code == 201, response.text


def test_ordering_is_attempts_then_duration(client: TestClient) -> None:
    post(client, player_name="slow", attempts=12, duration_seconds=200)
    post(client, player_name="fast", attempts=12, duration_seconds=90)
    post(client, player_name="sloppy", attempts=20, duration_seconds=30)
    post(client, player_name="perfect", attempts=8, duration_seconds=300)

    entries = client.get("/api/v1/leaderboard").json()["entries"]
    assert [entry["player_name"] for entry in entries] == [
        "perfect",
        "fast",
        "slow",
        "sloppy",
    ]
    assert [entry["rank"] for entry in entries] == [1, 2, 3, 4]


def test_difficulty_filter(client: TestClient) -> None:
    post(client, difficulty="easy", player_name="e")
    post(client, difficulty="hard", player_name="h")

    easy = client.get("/api/v1/leaderboard", params={"difficulty": "easy"}).json()
    hard = client.get("/api/v1/leaderboard", params={"difficulty": "hard"}).json()
    missing = client.get("/api/v1/leaderboard", params={"difficulty": "medium"}).json()

    assert [entry["player_name"] for entry in easy["entries"]] == ["e"]
    assert easy["total"] == 1
    assert [entry["player_name"] for entry in hard["entries"]] == ["h"]
    assert missing["entries"] == []
    assert missing["total"] == 0


def test_limit_truncates_but_total_counts_everything(client: TestClient) -> None:
    for index in range(5):
        post(client, player_name=f"p{index}", attempts=index + 1)

    board = client.get("/api/v1/leaderboard", params={"limit": 2}).json()
    assert board["total"] == 5
    assert board["limit"] == 2
    assert [entry["attempts"] for entry in board["entries"]] == [1, 2]
    assert [entry["rank"] for entry in board["entries"]] == [1, 2]


def test_default_limit_is_ten(client: TestClient) -> None:
    for index in range(12):
        post(client, player_name=f"p{index}", attempts=index + 1)

    board = client.get("/api/v1/leaderboard").json()
    assert board["limit"] == 10
    assert len(board["entries"]) == 10


@pytest.mark.parametrize("limit", [0, -1, 51, "abc"])
def test_invalid_limit_is_rejected(client: TestClient, limit: Any) -> None:
    response = client.get("/api/v1/leaderboard", params={"limit": limit})
    assert response.status_code == 422


def test_invalid_difficulty_is_rejected(client: TestClient) -> None:
    response = client.get("/api/v1/leaderboard", params={"difficulty": "expert"})
    assert response.status_code == 422


def test_ranking_is_stable_for_equal_scores(client: TestClient) -> None:
    post(client, player_name="first", attempts=10, duration_seconds=60)
    post(client, player_name="second", attempts=10, duration_seconds=60)

    entries = client.get("/api/v1/leaderboard").json()["entries"]
    assert [entry["player_name"] for entry in entries] == ["first", "second"]
