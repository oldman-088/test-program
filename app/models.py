"""ORM models for the game scores service."""

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Score(Base):
    """A single finished game round submitted by a player."""

    __tablename__ = "scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_name: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="CURRENT_TIMESTAMP"
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return (
            f"<Score id={self.id} player_name={self.player_name!r} "
            f"difficulty={self.difficulty!r} attempts={self.attempts} "
            f"duration_seconds={self.duration_seconds}>"
        )
