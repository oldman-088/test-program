"""مصنع تطبيق FastAPI — البند 21 · المهمة AATM-984687b7 · سطح /api من AATM-49a40f0c.

``create_app`` يقبل الإعدادات وكائن قاعدة البيانات صراحةً، حتى تبني الاختبارات
تطبيقاً على ملف SQLite مؤقت دون لمس أي حالة عامة أو خدمة خارجية.

كل مسارات العمل مركّبة تحت ``settings.api_v1_prefix`` (العقد الموثّق في
``docs/API.md``)، إضافةً إلى سطح ``/api`` العام (مسارا الصحة من AATM-49a40f0c)
الذي يوثّقه القسم الأخير من ``docs/API.md``. توثيق OpenAPI متاح على
``/openapi.json`` وعلى ``/api/openapi.json`` معاً.
"""

from __future__ import annotations

import logging
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse, RedirectResponse

from app import __version__
from app.api.router import api_router, public_api_router
from app.core.config import Settings, get_settings
from app.core.database import Database, build_database
from app.core.errors import new_request_id, register_exception_handlers
from app.core.logging import configure_logging

logger = logging.getLogger("app.main")

#: معرّف الطلب المقبول من العميل: أحرف آمنة فقط وبطول محدود (لا حقن ترويسة).
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

#: الوسوم الظاهرة في مخطط OpenAPI؛ يختبرها اختبار العقد كي لا يضاف مسار بلا وسم.
OPENAPI_TAGS: tuple[str, ...] = ("health", "sessions")


def create_app(settings: Settings | None = None, *, database: Database | None = None) -> FastAPI:
    """يبني التطبيق: التسجيل المُهيكل، CORS للوحة، الأخطاء الموحدة، مسارات ``/api/v1`` و``/api``.

    لا اتصال شبكي هنا: محرك SQL لا يفتح اتصالاً إلا عند أول استخدام.
    """
    settings = settings or get_settings()
    database = database or build_database(settings)
    configure_logging(settings.log_level)

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

    #: أصلان مسموحان للوحة: ``FRONTEND_ORIGIN`` (AATM-49a40f0c) ∪ ``CORS_ALLOW_ORIGINS``.
    cors_origins = list(dict.fromkeys([*settings.frontend_origins, *settings.cors_origins_list]))
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # كل حقن ``get_settings`` يرى الإعدادات الفعلية للتطبيق (لا النسخة المخزّنة عالمياً).
    app.dependency_overrides[get_settings] = lambda: settings

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
    #: سطح ``/api`` العام — مسارا الصحة بلا مصادقة (AATM-49a40f0c).
    app.include_router(public_api_router, prefix="/api")

    @app.get("/api/openapi.json", include_in_schema=False)
    async def openapi_under_api() -> JSONResponse:
        """مخطط OpenAPI تحت ``/api`` — نفس محتوى ``/openapi.json`` حرفياً."""
        return JSONResponse(app.openapi())

    @app.get("/api/docs", include_in_schema=False)
    async def docs_under_api() -> RedirectResponse:
        """Swagger UI تحت ``/api/docs`` يعاد توجيهه إلى ``/docs``."""
        return RedirectResponse("/docs")

    return app


#: للنشر المباشر (``uvicorn app.main:app``). الاختبارات تستخدم ``create_app``.
app = create_app()
