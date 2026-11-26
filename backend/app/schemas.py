"""Pydantic request/response schemas."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Difficulty = Literal["easy", "medium", "hard"]

PlayerName = Annotated[str, Field(min_length=1, max_length=40)]
Attempts = Annotated[int, Field(gt=0, le=10_000)]
DurationSeconds = Annotated[int, Field(gt=0, le=86_400)]


class ScoreCreate(BaseModel):
    """Payload sent by the game when a round finishes."""

    player_name: PlayerName
    difficulty: Difficulty
    attempts: Attempts
    duration_seconds: DurationSeconds
    finished_at: datetime | None = None

    @field_validator("player_name")
    @classmethod
    def strip_player_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("player_name must not be blank")
        return stripped

    @field_validator("finished_at")
    @classmethod
    def ensure_timezone(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class ScoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    player_name: str
    difficulty: Difficulty
    attempts: int
    duration_seconds: int
    finished_at: datetime


class LeaderboardEntry(ScoreRead):
    rank: int


class LeaderboardResponse(BaseModel):
    difficulty: Difficulty
    limit: int
    total: int
    entries: list[LeaderboardEntry]


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    version: str
