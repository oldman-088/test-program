"""مصنع تطبيق FastAPI — البند 21 · المهمة AATM-984687b7.

``create_app`` يقبل الإعدادات وكائن قاعدة البيانات صراحةً، حتى تبني الاختبارات
تطبيقاً على ملف SQLite مؤقت دون لمس أي حالة عامة أو خدمة خارجية.
"""

from __future__ import annotations

import logging
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response

from app import __version__
from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.database import Database, build_database
from app.core.errors import new_request_id, register_exception_handlers

logger = logging.getLogger("app.main")

#: معرّف الطلب المقبول من العميل: أحرف آمنة فقط وبطول محدود (لا حقن ترويسة).
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

#: الوسوم الظاهرة في مخطط OpenAPI؛ يختبرها اختبار العقد كي لا يضاف مسار بلا وسم.
OPENAPI_TAGS: tuple[str, ...] = ("health", "sessions")


def create_app(settings: Settings | None = None, *, database: Database | None = None) -> FastAPI:
    """يبني التطبيق. لا اتصال شبكي هنا: محرك SQL لا يفتح اتصالاً إلا عند أول استخدام."""
    settings = settings or get_settings()
    database = database or build_database(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logger.info("backend started (env=%s)", settings.environment)
        yield
        database.dispose()

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        debug=settings.debug,
        openapi_tags=[{"name": tag} for tag in OPENAPI_TAGS],
        docs_url="/docs",
        redoc_url=None,
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.database = database

    register_exception_handlers(app)

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next) -> Response:
        """يوثّق كل طلب بمعرّف ويعيد نفس الترويسة في الاستجابة (نجاحاً وفشلاً)."""
        incoming = request.headers.get(settings.request_id_header) or ""
        request_id = incoming if REQUEST_ID_PATTERN.match(incoming) else new_request_id()
        request.state.request_id = request_id
        response: Response = await call_next(request)
        response.headers[settings.request_id_header] = request_id
        return response

    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


#: للنشر المباشر (``uvicorn app.main:app``). الاختبارات تستخدم ``create_app``.
app = create_app()
