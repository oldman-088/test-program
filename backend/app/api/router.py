"""مُجمِّع موجّهات المنصّة — ``api_router`` يُركَّب على ``settings.api_v1_prefix``.

``public_api_router`` هو سطح ``/api`` العام (مسارا الصحة من AATM-49a40f0c) ويُركَّب
على ``/api`` مباشرة في ``app.main`` — بلا تغيير في العقد الموثّق لـ ``/api/v1``.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api import health as public_health
from app.api.routes import health, sessions

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(sessions.router)

#: سطح ``/api`` العام — مسارا الصحة (liveness + connectivity) بلا مصادقة.
public_api_router = APIRouter()
public_api_router.include_router(public_health.router)

__all__ = ["api_router", "public_api_router"]
