"""قالب الخطأ الموحد — البند 21 · المهمة AATM-984687b7.

كل استجابة خطأ (بما فيها أخطاء التوثيق 404 وأخطاء التحقق من Pydantic وأخطاء
المعالجة 500) تمرّ من ``error_envelope`` وحده، فلا يوجد أي مسار يُخرج JSON بشكل مختلف.

    {
      "error": {
        "code": "not_found",
        "message": "…",
        "details": [],
        "request_id": "…"
      }
    }

أي تغيير في المفاتيح أو في خريطة الأكواد↔حالات HTTP يكسر ``tests/test_contract.py``
و``tests/test_errors.py`` معاً.
"""

from __future__ import annotations

import logging
import uuid
from http import HTTPStatus
from typing import Any, ClassVar

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

from app.core.database import DatabaseUnavailableError

logger = logging.getLogger("app.errors")

#: أسماء المفاتيح الأربعة داخل ``error`` — العقد الموثّق في ``docs/API.md``.
ENVELOPE_ROOT_KEY: str = "error"
ENVELOPE_FIELDS: tuple[str, ...] = ("code", "message", "details", "request_id")


class APIError(Exception):
    """الأب لكل أخطاء التطبيق المقصودة. لا تُسرّب تفاصيل داخلية في ``message``."""

    code: ClassVar[str] = "api_error"
    status_code: ClassVar[int] = 500
    #: رسالة افتراضية عامة تظهر حين لا يعطي الرامي رسالة صريحة.
    default_detail: ClassVar[str] = "تعذّر إتمام الطلب."

    def __init__(
        self,
        message: str | None = None,
        *,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        self.message = message or self.default_detail
        self.details: list[dict[str, Any]] = list(details or [])
        super().__init__(self.message)

    def to_envelope(self, request_id: str | None = None) -> dict[str, Any]:
        return error_envelope(self.code, self.message, details=self.details, request_id=request_id)


class ValidationError_(APIError):  # الاسم يتفادى الظل مع pydantic.ValidationError
    code: ClassVar[str] = "validation_error"
    status_code: ClassVar[int] = 422
    default_detail: ClassVar[str] = "بيانات الطلب غير صالحة."


class AuthenticationError(APIError):
    code: ClassVar[str] = "unauthenticated"
    status_code: ClassVar[int] = 401
    default_detail: ClassVar[str] = "مطلوب تقديم بيانات اعتماد صالحة."


class PermissionDeniedError(APIError):
    code: ClassVar[str] = "permission_denied"
    status_code: ClassVar[int] = 403
    default_detail: ClassVar[str] = "لا تملك صلاحية لهذا المورد."


class NotFoundError(APIError):
    code: ClassVar[str] = "not_found"
    status_code: ClassVar[int] = 404
    default_detail: ClassVar[str] = "المطلوب غير موجود."


class ConflictError(APIError):
    code: ClassVar[str] = "conflict"
    status_code: ClassVar[int] = 409
    default_detail: ClassVar[str] = "تعارض مع حالة حالية."


class ConfigurationError(APIError):
    code: ClassVar[str] = "configuration_error"
    status_code: ClassVar[int] = 500
    default_detail: ClassVar[str] = "إعداد ناقص على الخادم."


class UpstreamError(APIError):
    code: ClassVar[str] = "upstream_unavailable"
    status_code: ClassVar[int] = 502
    default_detail: ClassVar[str] = "الخدمة الخارجية غير متاحة حالياً."


class DatabaseError(APIError):
    code: ClassVar[str] = "database_unavailable"
    status_code: ClassVar[int] = 503
    default_detail: ClassVar[str] = "قاعدة البيانات غير متاحة حالياً."


#: قائمة الأكواد المعتمدة؛ يُقارنها اختبار العقد بجدول الأخطاء في ``docs/API.md`` في الاتجاهين.
ERROR_REGISTRY: dict[str, type[APIError]] = {
    cls.code: cls
    for cls in (
        ValidationError_,
        AuthenticationError,
        PermissionDeniedError,
        NotFoundError,
        ConflictError,
        ConfigurationError,
        UpstreamError,
        DatabaseError,
        APIError,
    )
}

#: خرائط حالات HTTP التي تطلقها Starlette نفسها (404 مسار غير معروف، 405 …).
HTTP_STATUS_TO_CODE: dict[int, str] = {
    400: "bad_request",
    401: "unauthenticated",
    403: "permission_denied",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "payload_too_large",
    422: "validation_error",
    429: "rate_limited",
    500: "internal_error",
    503: "database_unavailable",
}


def error_envelope(
    code: str,
    message: str,
    *,
    details: list[dict[str, Any]] | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    """المصدر الوحيد لبناء جسم الخطأ. المفاتيح ثابتة دائماً."""
    return {
        ENVELOPE_ROOT_KEY: {
            "code": code,
            "message": message,
            "details": list(details or []),
            "request_id": request_id,
        }
    }


def new_request_id() -> str:
    return uuid.uuid4().hex


def request_id_of(request: Request | None) -> str | None:
    if request is None:
        return None
    return getattr(request.state, "request_id", None)


def _json_error(
    status_code: int,
    code: str,
    message: str,
    details: list[dict[str, Any]] | None,
    request_id: str | None,
) -> JSONResponse:
    headers = {"X-Error-Code": code}
    if request_id:
        headers["X-Request-ID"] = request_id
    return JSONResponse(
        status_code=status_code,
        content=error_envelope(code, message, details=details, request_id=request_id),
        headers=headers,
    )


def _raw_errors(exc: ValidationError | RequestValidationError) -> list[dict[str, Any]]:
    """قائمة أخطاء موحّدة من Pydantic أو من FastAPI/Starlette.

    ``RequestValidationError.errors()`` في Starlette لا يقبل الوسائط، ويعيد مفاتيح
    إضافية (``url``/``ctx``) — تُحذف هنا حتى يبقى شكل ``details`` ثابتاً من المصدرين.
    """
    try:
        raw = list(exc.errors(include_url=False, include_context=False))  # type: ignore[call-arg]
    except TypeError:
        raw = list(exc.errors())
    for entry in raw:
        entry.pop("url", None)
        entry.pop("ctx", None)
    return raw


def _validation_details(exc: ValidationError | RequestValidationError) -> list[dict[str, Any]]:
    """تفاصيل تحققات Pydantic — مفاتيحها الأربعة جزء من العقد الموثّق."""
    items: list[dict[str, Any]] = []
    for err in _raw_errors(exc):
        loc = [str(part) for part in err.get("loc", ())]
        items.append(
            {
                "field": ".".join(loc[1:]) or (loc[0] if loc else ""),
                "loc": loc,
                "message": str(err.get("msg", "invalid value")),
                "type": str(err.get("type", "value_error")),
            }
        )
    return items


def register_exception_handlers(app: FastAPI) -> None:
    """يسجّل كل المعالجات. تُنادى مرة واحدة من ``create_app``."""

    @app.exception_handler(APIError)
    async def _handle_api_error(request: Request, exc: APIError) -> JSONResponse:
        return _json_error(exc.status_code, exc.code, exc.message, exc.details, request_id_of(request))

    @app.exception_handler(RequestValidationError)
    async def _handle_request_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = _validation_details(exc)
        message = f"تحقق واحد على الأقل فشل ({len(details)})." if details else "بيانات الطلب غير صالحة."
        return _json_error(422, "validation_error", message, details, request_id_of(request))

    @app.exception_handler(ValidationError)  # pydantic مباشرة (خارج مسار FastAPI)
    async def _handle_pydantic_validation(request: Request, exc: ValidationError) -> JSONResponse:
        return _json_error(
            422,
            "validation_error",
            "بيانات الطلب غير صالحة.",
            _validation_details(exc),
            request_id_of(request),
        )

    @app.exception_handler(DatabaseUnavailableError)
    async def _handle_db_unavailable(request: Request, exc: DatabaseUnavailableError) -> JSONResponse:
        logger.warning("database unavailable: %s", exc)
        return _json_error(
            503,
            DatabaseError.code,
            DatabaseError.default_detail,
            None,
            request_id_of(request),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = HTTP_STATUS_TO_CODE.get(exc.status_code, f"http_{exc.status_code}")
        detail = exc.detail if isinstance(exc.detail, str) else HTTPStatus(exc.status_code).phrase
        return _json_error(exc.status_code, code, detail, None, request_id_of(request))

    @app.exception_handler(Exception)
    async def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        # لا تُسرّب نص الاستثناء: يُسجّل فقط. انظر ``tests/test_errors.py``.
        logger.exception("unhandled error while processing %s", request.url.path)
        return _json_error(
            500,
            "internal_error",
            "خطأ داخلي غير متوقع.",
            None,
            request_id_of(request),
        )
