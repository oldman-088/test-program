"""مستودعات الوصول إلى البيانات — منطق SQL فقط، بلا أي اعتماد على HTTP."""

from __future__ import annotations

from app.repositories.sessions import SessionRepository

__all__ = ["SessionRepository"]
