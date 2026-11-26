"""نموذج جلسة العامل (``agent_sessions``) — دورة إنشاء/قراءة/حذف مُختبَرة كاملة."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import ClassVar

from sqlalchemy import DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

#: الحالات المقبولة. الوثيقة ``docs/API.md`` تعرض القائمة نفسها، واختبار العقد يقارنها.
SESSION_STATUSES: tuple[str, ...] = ("queued", "running", "review", "completed", "failed")


def _utcnow() -> datetime:
    """وقت UTC بلا منطقة زمنية — تخزين SQLite نصّي، والمقارنات تبقى صحيحة."""
    return datetime.now(UTC).replace(tzinfo=None)


def new_session_id() -> str:
    return f"ses_{uuid.uuid4().hex[:20]}"


class AgentSession(Base):
    __tablename__ = "agent_sessions"
    __table_args__ = (
        UniqueConstraint("task_id", name="uq_agent_sessions_task_id"),
        Index("ix_agent_sessions_employee_status", "employee_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=new_session_id)
    #: معرّف المهمة (AATM) المرتبطة بالجلسة — فريد لمنع تنفيذ المهمة مرتين.
    task_id: Mapped[str] = mapped_column(String(64), nullable=False)
    employee_id: Mapped[str] = mapped_column(String(64), nullable=False)
    branch: Mapped[str] = mapped_column(String(255), nullable=False)
    worktree: Mapped[str | None] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    #: عدد محاولات التنفيذ؛ ``>= MAX_ATTEMPTS`` يعني أن الجلسّة ميئوس منها.
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    #: آخر إشارة حياة من العامل (تُضيفها الهجرة 0002 — يقارنها اختبار التنازول التصاعدي).
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime())
    created_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    MAX_ATTEMPTS: ClassVar[int] = 3

    def __repr__(self) -> str:  # pragma: no cover - للتشخيص فقط
        return f"<AgentSession id={self.id!r} status={self.status!r}>"
