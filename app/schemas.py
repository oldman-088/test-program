"""Pydantic schemas for request/response payloads."""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_PLAYER_NAME_LENGTH = 40
MAX_ATTEMPTS = 10000
MAX_DURATION_SECONDS = 86400  # one day; anything longer is not a game round
DEFAULT_LEADERBOARD_LIMIT = 10
MAX_LEADERBOARD_LIMIT = 50


def _as_utc(value: datetime) -> datetime:
    """Treat naive datetimes as UTC and convert aware ones to UTC.

    SQLite stores datetimes without timezone information and returns them
    naive; normalizing to UTC here keeps instants correct and lets Pydantic
    serialize every datetime with an explicit ``Z`` suffix.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class Difficulty(StrEnum):
    """Supported game difficulties."""

    easy = "easy"
    medium = "medium"
    hard = "hard"


class ScoreCreate(BaseModel):
    """Payload accepted by POST /api/v1/scores."""

    player_name: str = Field(min_length=1, max_length=MAX_PLAYER_NAME_LENGTH)
    difficulty: Difficulty
    attempts: int = Field(gt=0, le=MAX_ATTEMPTS)
    duration_seconds: float = Field(gt=0, le=MAX_DURATION_SECONDS)
    finished_at: datetime | None = None

    @field_validator("player_name")
    @classmethod
    def _strip_player_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("player_name must not be blank")
        return stripped

    @field_validator("finished_at")
    @classmethod
    def _finished_at_to_utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _as_utc(value)


class ScoreOut(BaseModel):
    """A stored score, as returned by POST /api/v1/scores."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    player_name: str
    difficulty: Difficulty
    attempts: int
    duration_seconds: float
    finished_at: datetime
    created_at: datetime

    @field_validator("finished_at", "created_at")
    @classmethod
    def _datetimes_to_utc(cls, value: datetime) -> datetime:
        return _as_utc(value)


class LeaderboardEntry(BaseModel):
    """One ranked row of the leaderboard."""

    model_config = ConfigDict(from_attributes=True)

    rank: int
    id: int
    player_name: str
    difficulty: Difficulty
    attempts: int
    duration_seconds: float
    finished_at: datetime

    @field_validator("finished_at")
    @classmethod
    def _datetimes_to_utc(cls, value: datetime) -> datetime:
        return _as_utc(value)
