"""مسار الصحة (public). نقطة ``ready`` تفحص قاعدة البيانات فعلياً."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app import __version__
from app.core.database import Database, DatabaseUnavailableError
from app.core.errors import DatabaseError

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness probe", operation_id="healthCheck")
async def health(request: Request) -> dict[str, object]:
    """
    حالة العملية فقط — لا يلمس قاعدة البيانات، فيبقى صالحاً حتى لو كانت القاعدة معطّلة.

    حالة النجاح الموثّقة: ``200`` مع ``{"status":"ok"}``.
    """
    settings = request.app.state.settings
    return {
        "status": "ok",
        "version": __version__,
        "environment": settings.environment,
    }


@router.get("/health/ready", summary="Readiness: DB connectivity", operation_id="healthReadiness")
async def health_ready(request: Request) -> dict[str, str]:
    """
    ``200`` حين تستجيب القاعدة؛ ``503`` بقالب الخطأ الموحد (``database_unavailable``)
    حين تفشل ``SELECT 1``. لا شيء ثالث — لا ``200`` كاذبة.
    """
    database: Database = request.app.state.database
    try:
        database.ping()
    except DatabaseUnavailableError as exc:
        raise DatabaseError() from exc
    return {"status": "ready", "database": "up"}
