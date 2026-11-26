"""0002: عمود ``last_heartbeat_at`` على ``agent_sessions``.

revision: 0002  ←  0001

وُجدت هذه الهجرة بعد 0001 لإثبات أن التدرّج (chain) يعمل صعوداً ونزولاً على قاعدة
مؤقتة: يختبر ``backend/tests/test_database.py`` أن ``upgrade head`` يضيف العمود،
وأن ``downgrade 0001`` يحذفه مع بقاء الجدول، وأن ``downgrade base`` يحذف الجدول كله.
التسلسل مقصود: لو كانت التسمية أو ``down_revision`` خاطئة يفشل الاختبار فوراً.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "agent_sessions"
COLUMN = "last_heartbeat_at"


def upgrade() -> None:
    # SQLite لا يدعم ALTER الكامل؛ batch_alter_table هو المسار الصحيح على كل اللهجات.
    with op.batch_alter_table(TABLE) as batch:
        batch.add_column(sa.Column(COLUMN, sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table(TABLE) as batch:
        batch.drop_column(COLUMN)
