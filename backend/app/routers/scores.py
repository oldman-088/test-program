"""HTTP endpoints: health, score submission, leaderboard, stats."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import __version__
from app.database import get_db
from app.models import Score
from app.schemas import (
    Difficulty,
    HealthResponse,
    LeaderboardEntry,
    LeaderboardResponse,
    ScoreCreate,
    ScoreRead,
)

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]

RANKING_ORDER = (
    Score.attempts.asc(),
    Score.duration_seconds.asc(),
    Score.finished_at.asc(),
    Score.id.asc(),
)


@router.get("/health", response_model=HealthResponse, tags=["meta"])
def health() -> HealthResponse:
    return HealthResponse(status="ok", version=__version__)


@router.post(
    "/api/v1/scores",
    response_model=ScoreRead,
    status_code=status.HTTP_201_CREATED,
    tags=["scores"],
)
def create_score(payload: ScoreCreate, db: DbSession) -> Score:
    score = Score(
        player_name=payload.player_name,
        difficulty=payload.difficulty,
        attempts=payload.attempts,
        duration_seconds=payload.duration_seconds,
        finished_at=payload.finished_at or datetime.now(UTC),
    )
    db.add(score)
    db.commit()
    db.refresh(score)
    return score


@router.get("/api/v1/leaderboard", response_model=LeaderboardResponse, tags=["scores"])
def leaderboard(
    db: DbSession,
    difficulty: Annotated[Difficulty, Query(description="Which board to read")] = "easy",
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> LeaderboardResponse:
    base = select(Score).where(Score.difficulty == difficulty)
    entries = db.scalars(base.order_by(*RANKING_ORDER).limit(limit)).all()
    total = db.scalar(
        select(func.count(Score.id)).where(Score.difficulty == difficulty)
    )
    return LeaderboardResponse(
        difficulty=difficulty,
        limit=limit,
        total=int(total or 0),
        entries=[
            LeaderboardEntry(rank=index + 1, **ScoreRead.model_validate(row).model_dump())
            for index, row in enumerate(entries)
        ],
    )


@router.get("/api/v1/stats", tags=["meta"])
def stats(db: DbSession) -> dict[str, dict[str, int | None]]:
    rows = db.execute(
        select(
            Score.difficulty,
            func.count(Score.id),
            func.min(Score.attempts),
            func.min(Score.duration_seconds),
        ).group_by(Score.difficulty)
    ).all()
    return {
        difficulty: {"games": games, "best_attempts": best, "best_duration": fastest}
        for difficulty, games, best, fastest in rows
    }
