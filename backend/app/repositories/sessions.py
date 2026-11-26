"""مستودع الجلسات: دورة إنشاء/قراءة/حذف كاملة على أي ``Session``."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.models.session import AgentSession


class SessionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, *, task_id: str, employee_id: str, branch: str, worktree: str | None = None) -> AgentSession:
        """ينشئ سجلّاً جديداً بحالة ``queued``. تعارض ``task_id`` ⇒ 409 (منع تنفيذ المهمة مرتين)."""
        if self.get_by_task_id(task_id) is not None:
            raise ConflictError(f"مهمة {task_id} مرتبطة بالفعل بجلسة قائمة.")
        record = AgentSession(
            task_id=task_id,
            employee_id=employee_id,
            branch=branch,
            worktree=worktree,
        )
        self._session.add(record)
        self._session.flush()  # يكتب حتى تُطبَّق القيود ويُعبَّأ id الافتراضي
        return record

    def get(self, session_id: str) -> AgentSession:
        """مثل ``get_or_404`` — يرفع خطأ التطبيق لا ``None``."""
        record = self._session.get(AgentSession, session_id)
        if record is None:
            raise NotFoundError(f"الجلسة {session_id} غير موجودة.")
        return record

    def get_by_task_id(self, task_id: str) -> AgentSession | None:
        stmt = select(AgentSession).where(AgentSession.task_id == task_id)
        return self._session.scalar(stmt)

    def list_for_employee(self, employee_id: str, *, limit: int = 20) -> list[AgentSession]:
        stmt = (
            select(AgentSession)
            .where(AgentSession.employee_id == employee_id)
            .order_by(AgentSession.created_at.desc(), AgentSession.id.desc())
            .limit(limit)
        )
        return list(self._session.scalars(stmt))

    def mark_status(self, session_id: str, status: str) -> AgentSession:
        record = self.get(session_id)
        record.status = status
        self._session.flush()
        return record

    def delete(self, session_id: str) -> None:
        """حذف فعلي. غيّر المعرّف ⇒ 404 (مسار الفشل الموثّق)."""
        record = self.get(session_id)
        self._session.delete(record)
        self._session.flush()
