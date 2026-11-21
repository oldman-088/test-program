"""Tests for the Alembic migration state of the per-test database."""

from datetime import UTC

from sqlalchemy import inspect, text


def test_migrations_created_scores_table(db_session):
    inspector = inspect(db_session.connection())
    assert inspector.has_table("scores")

    columns = {column["name"] for column in inspector.get_columns("scores")}
    expected_columns = {
        "id",
        "player_name",
        "difficulty",
        "attempts",
        "duration_seconds",
        "finished_at",
        "created_at",
    }
    assert expected_columns <= columns


def test_migrations_are_at_head_revision(db_session):
    current = db_session.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert current == "0001"


def test_round_trip_insert_and_query(db_session):
    from datetime import datetime

    from app.models import Score

    score = Score(
        player_name="layla",
        difficulty="hard",
        attempts=2,
        duration_seconds=33.3,
        finished_at=datetime.now(UTC),
    )
    db_session.add(score)
    db_session.commit()
    db_session.refresh(score)

    assert score.id is not None
    assert score.created_at is not None

    stored = db_session.get(Score, score.id)
    assert stored is not None
    assert stored.player_name == "layla"
    assert stored.attempts == 2
