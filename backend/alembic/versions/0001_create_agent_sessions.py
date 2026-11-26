"""0001: جدول ``agent_sessions``.

المهمة AATM-984687b7 — الترحيل الأول الذي يثبّت اختبارُ القاعدة أنه يعمل صعوداً ونزولاً.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "agent_sessions"


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column("id", sa.String(length=40), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("employee_id", sa.String(length=64), nullable=False),
        sa.Column("branch", sa.String(length=255), nullable=False),
        sa.Column("worktree", sa.String(length=512), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_agent_sessions")),
        sa.UniqueConstraint("task_id", name=op.f("uq_agent_sessions_task_id")),
    )
    op.create_index(
        op.f("ix_agent_sessions_employee_status"),
        TABLE,
        ["employee_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_agent_sessions_employee_status"), table_name=TABLE)
    op.drop_table(TABLE)
