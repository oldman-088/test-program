"""Pydantic schemas for request/response payloads."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_PLAYER_NAME_LENGTH = 40
MAX_ATTEMPTS = 10000
MAX_DURATION_SECONDS = 86400  # one day; anything longer is not a game round
DEFAULT_LEADERBOARD_LIMIT = 10
MAX_LEADERBOARD_LIMIT = 50


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
