"""create scores table

Revision ID: 0001
Revises:
Create Date: 2026-11-21

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scores",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("player_name", sa.String(length=40), nullable=False),
        sa.Column("difficulty", sa.String(length=10), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_scores_player_name"), "scores", ["player_name"], unique=False)
    op.create_index(op.f("ix_scores_difficulty"), "scores", ["difficulty"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_scores_difficulty"), table_name="scores")
    op.drop_index(op.f("ix_scores_player_name"), table_name="scores")
    op.drop_table("scores")
