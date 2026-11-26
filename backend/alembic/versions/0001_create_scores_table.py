"""create scores table

Revision ID: 0001
Revises:
Create Date: 2026-11-26 00:00:00

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scores",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("player_name", sa.String(length=40), nullable=False),
        sa.Column(
            "difficulty",
            sa.Enum("easy", "medium", "hard", name="difficulty_enum", native_enum=False, length=16),
            nullable=False,
        ),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_scores_difficulty_rank",
        "scores",
        ["difficulty", "attempts", "duration_seconds"],
    )
    op.create_index("ix_scores_finished_at", "scores", ["finished_at"])


def downgrade() -> None:
    op.drop_index("ix_scores_finished_at", table_name="scores")
    op.drop_index("ix_scores_difficulty_rank", table_name="scores")
    op.drop_table("scores")
