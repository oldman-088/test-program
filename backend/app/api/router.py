"""مُجمِّع موجّهات المنصّة — ``api_router`` هو كل ما يُثبَّت على التطبيق."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import health, sessions

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(sessions.router)

__all__ = ["api_router"]
