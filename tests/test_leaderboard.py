"""Tests for GET /api/v1/leaderboard ordering, filtering and limit."""

import pytest


def _post_score(client, player_name, difficulty, attempts, duration_seconds):
    response = client.post(
        "/api/v1/scores",
        json={
            "player_name": player_name,
            "difficulty": difficulty,
            "attempts": attempts,
            "duration_seconds": duration_seconds,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_leaderboard_orders_by_attempts_then_duration(client):
    _post_score(client, "dalia", "easy", attempts=5, duration_seconds=10.0)
    _post_score(client, "hadi", "easy", attempts=3, duration_seconds=99.0)
    _post_score(client, "yara", "easy", attempts=3, duration_seconds=20.0)
    _post_score(client, "samir", "easy", attempts=7, duration_seconds=1.0)

    response = client.get("/api/v1/leaderboard")

    assert response.status_code == 200
    rows = response.json()
    assert [(row["player_name"], row["attempts"], row["duration_seconds"]) for row in rows] == [
        ("yara", 3, 20.0),
        ("hadi", 3, 99.0),
        ("dalia", 5, 10.0),
        ("samir", 7, 1.0),
    ]
    assert [row["rank"] for row in rows] == [1, 2, 3, 4]


def test_leaderboard_difficulty_filter(client):
    _post_score(client, "easy_a", "easy", attempts=1, duration_seconds=5.0)
    _post_score(client, "hard_a", "hard", attempts=2, duration_seconds=6.0)
    _post_score(client, "easy_b", "easy", attempts=3, duration_seconds=7.0)
    _post_score(client, "medium_a", "medium", attempts=4, duration_seconds=8.0)
    _post_score(client, "hard_b", "hard", attempts=5, duration_seconds=9.0)

    response = client.get("/api/v1/leaderboard", params={"difficulty": "hard"})

    assert response.status_code == 200
    rows = response.json()
    assert [row["player_name"] for row in rows] == ["hard_a", "hard_b"]
    assert all(row["difficulty"] == "hard" for row in rows)

    response = client.get("/api/v1/leaderboard", params={"difficulty": "easy"})

    assert response.status_code == 200
    assert [row["player_name"] for row in response.json()] == ["easy_a", "easy_b"]


def test_leaderboard_limit_respected(client):
    for index in range(6):
        _post_score(client, f"player_{index}", "medium", attempts=index + 2, duration_seconds=10.0)

    response = client.get("/api/v1/leaderboard")
    assert response.status_code == 200
    assert len(response.json()) == 6  # default limit of 10 does not truncate

    response = client.get("/api/v1/leaderboard", params={"limit": 3})
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 3
    assert [row["attempts"] for row in rows] == [2, 3, 4]  # the best three


def test_leaderboard_limit_out_of_bounds_rejected(client):
    for bad_limit in (0, -1, 51, 1000):
        response = client.get("/api/v1/leaderboard", params={"limit": bad_limit})
        assert response.status_code == 422, f"limit={bad_limit} should be rejected"


@pytest.mark.parametrize("bad_difficulty", ["impossible", "", "EASY", 42])
def test_leaderboard_invalid_difficulty_rejected(client, bad_difficulty):
    response = client.get("/api/v1/leaderboard", params={"difficulty": bad_difficulty})

    assert response.status_code == 422


def test_leaderboard_empty_is_empty_list(client):
    response = client.get("/api/v1/leaderboard")

    assert response.status_code == 200
    assert response.json() == []
