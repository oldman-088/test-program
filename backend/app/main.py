"""FastAPI application factory.

Run locally from ``backend/``::

    uvicorn app.main:app --reload

Every route is mounted under ``/api`` (OpenAPI at ``/api/openapi.json``, docs at
``/api/docs`` and ``/api/redoc``). The contract for success/error shapes, timestamps
and pagination is defined in ``docs/API.md`` — the single source of truth.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the application: logging, CORS for the dashboard, unified errors, ``/api`` routes."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.frontend_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)
    app.include_router(api_router, prefix="/api")
    if settings is not None:
        # Let tests/instances inject concrete settings instead of the cached global ones.
        app.dependency_overrides[get_settings] = lambda: settings
    return app


app = create_app()
