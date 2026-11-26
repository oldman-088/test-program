"""تبعيات FastAPI المشتركة: المصادقة وجلسة قاعدة البيانات (القاعدة Q5)."""

from __future__ import annotations

import secrets
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.database import Database
from app.core.errors import AuthenticationError, ConfigurationError


def get_settings_state(request: Request) -> Settings:
    return request.app.state.settings


def get_database_state(request: Request) -> Database:
    return request.app.state.database


def get_db(request: Request) -> Iterator[Session]:
    """جلسة واحدة لكل طلب: commit عند النجاح، rollback عند الفشل، إغلاق دائماً."""
    database: Database = get_database_state(request)
    with database.session() as session:
        yield session


def require_api_key(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings_state)],
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> None:
    """
    حماية نقاط العمل بمفتاح API.

    * لا مفتاح ``X-API-Key`` أو مفتاح خاطئ ⇒ ``AuthenticationError`` (401).
    * لم يُضبط ``API_KEY`` على الخادم ⇒ ``ConfigurationError`` (500): الفشل مغلق،
      لا يُسمح بأي طلب على خادم بلا سرّ.
    """
    expected = settings.api_key.get_secret_value()
    if not expected:
        raise ConfigurationError("لم تُضبط API_KEY؛ نقاط العمل مغلقة حتى يُعيَّن مفتاح.")
    supplied = (x_api_key or "").strip()
    if not supplied or not secrets.compare_digest(supplied, expected):
        raise AuthenticationError()


SettingsDep = Annotated[Settings, Depends(get_settings_state)]
DatabaseDep = Annotated[Database, Depends(get_database_state)]
DbDep = Annotated[Session, Depends(get_db)]
AuthDep = Annotated[None, Depends(require_api_key)]
