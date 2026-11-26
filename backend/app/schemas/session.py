"""مخططات Pydantic لجلسات العمل (العقد الخارجي لا نموذج قاعدة البيانات)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.session import SESSION_STATUSES


class SessionCreate(BaseModel):
    """جسم ``POST /api/v1/sessions``."""

    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(min_length=8, max_length=64, description="معرّف AATM للمهمة.")
    employee_id: str = Field(min_length=1, max_length=64, description="معرّف العامل.")
    branch: str = Field(min_length=1, max_length=255, description="فرع العمل في worktree.")
    worktree: str | None = Field(default=None, max_length=512)

    @field_validator("task_id", "employee_id", "branch", "worktree")
    @classmethod
    def _no_surrounding_space(cls, value: str | None) -> str | None:
        """trims ثم يرفض أي قيمة تصبح فارغة — لا مسارات فضفاضة في قاعدة البيانات."""
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be blank")
        if cleaned != value:
            raise ValueError("must not have surrounding whitespace")
        return cleaned


class SessionRead(BaseModel):
    """جسم الاستجابة. ``from_attributes`` يسمح بتمرير نموذج ORM مباشرة."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    task_id: str
    employee_id: str
    branch: str
    worktree: str | None
    status: str
    attempts: int
    created_at: datetime
    updated_at: datetime

    @field_validator("status")
    @classmethod
    def _known_status(cls, value: str) -> str:
        if value not in SESSION_STATUSES:
            raise ValueError(f"status must be one of: {', '.join(SESSION_STATUSES)}")
        return value
