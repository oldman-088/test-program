"""SQLAlchemy ORM models."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, Enum, Index, Integer, String, TypeDecorator
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UTCDateTime(TypeDecorator[datetime]):
    """Store naive UTC in the database, always hand back timezone-aware UTC.

    SQLite drops tzinfo on round-trips; this decorator keeps API responses
    consistent between SQLite and PostgreSQL.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class Score(Base):
    """One completed game.

    ``attempts`` counts pair reveal attempts (each pair flip costs one attempt),
    ``duration_seconds`` is the wall-clock duration of the game.
    """

    __tablename__ = "scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_name: Mapped[str] = mapped_column(String(40), nullable=False)
    difficulty: Mapped[str] = mapped_column(
        Enum("easy", "medium", "hard", name="difficulty_enum", native_enum=False, length=16),
        nullable=False,
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    finished_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index("ix_scores_difficulty_rank", "difficulty", "attempts", "duration_seconds"),
        Index("ix_scores_finished_at", "finished_at"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"Score(id={self.id!r}, player_name={self.player_name!r}, "
            f"difficulty={self.difficulty!r}, attempts={self.attempts!r}, "
            f"duration_seconds={self.duration_seconds!r})"
        )
