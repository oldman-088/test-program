"""Score submission and leaderboard endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Score
from app.schemas import (
    DEFAULT_LEADERBOARD_LIMIT,
    MAX_LEADERBOARD_LIMIT,
    Difficulty,
    LeaderboardEntry,
    ScoreCreate,
    ScoreOut,
)

router = APIRouter()


@router.post(
    "/scores",
    response_model=ScoreOut,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a finished game round",
)
def create_score(payload: ScoreCreate, db: Session = Depends(get_db)) -> Score:
    """Store one finished round and return it with its generated id."""
    score = Score(
        player_name=payload.player_name,
        difficulty=payload.difficulty.value,
        attempts=payload.attempts,
        duration_seconds=payload.duration_seconds,
        finished_at=payload.finished_at or datetime.now(UTC),
    )
    db.add(score)
    db.commit()
    db.refresh(score)
    return score


@router.get("/leaderboard", response_model=list[LeaderboardEntry], summary="Top scores")
def leaderboard(
    difficulty: Difficulty | None = Query(default=None),
    limit: int = Query(
        default=DEFAULT_LEADERBOARD_LIMIT, ge=1, le=MAX_LEADERBOARD_LIMIT
    ),
    db: Session = Depends(get_db),
) -> list[LeaderboardEntry]:
    """Return the best results: fewest attempts first, then shortest duration."""
    stmt = select(Score)
    if difficulty is not None:
        stmt = stmt.where(Score.difficulty == difficulty.value)
    stmt = stmt.order_by(
        Score.attempts.asc(), Score.duration_seconds.asc(), Score.finished_at.asc()
    ).limit(limit)

    rows = db.scalars(stmt).all()
    return [
        LeaderboardEntry(
            rank=index,
            id=row.id,
            player_name=row.player_name,
            difficulty=Difficulty(row.difficulty),
            attempts=row.attempts,
            duration_seconds=row.duration_seconds,
            finished_at=row.finished_at,
        )
        for index, row in enumerate(rows, start=1)
    ]
