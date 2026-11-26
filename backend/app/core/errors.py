"""Unified error contract for every API failure.

Every error response uses one template (documented in ``docs/API.md``)::

    {
        "error": {
            "code": "snake_case_machine_code",
            "message": "Human-readable message.",
            "details": null | object | array
        }
    }

Handlers are registered for:

* ``StarletteHTTPException`` (all ``HTTPException`` raises, including 404/405 from routing),
* ``fastapi.exceptions.RequestValidationError`` (invalid request bodies/query params -> 422),
* ``pydantic.ValidationError`` (response-model bugs -> 500, logged),
* unhandled ``Exception`` (-> 500 ``internal_error``, logged with stack trace, no internals leaked).

Routes may customise the payload by raising ``HTTPException(status, {"code": ..., "message": ...,
"details": ...})`` with a dict detail.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

DEFAULT_CODE_BY_STATUS: dict[int, str] = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    422: "validation_error",
    429: "rate_limited",
    500: "internal_error",
    503: "service_unavailable",
}

DEFAULT_MESSAGE_BY_STATUS: dict[int, str] = {
    400: "Malformed request.",
    401: "Authentication required.",
    403: "Insufficient permissions.",
    404: "Resource not found.",
    405: "Method not allowed.",
    409: "Conflict with current state.",
    422: "Request validation failed.",
    429: "Too many requests.",
    500: "An unexpected error occurred.",
    503: "Service temporarily unavailable.",
}


class ErrorBody(BaseModel):
    """Machine-readable error payload."""

    code: str = Field(..., examples=["not_found"])
    message: str = Field(..., examples=["Resource not found."])
    details: dict[str, Any] | list[Any] | None = Field(default=None)


class ErrorResponse(BaseModel):
    """The single error template every failure response uses."""

    error: ErrorBody


def _error_payload(
    status_code: int,
    code: str | None = None,
    message: str | None = None,
    details: dict[str, Any] | list[Any] | None = None,
) -> dict[str, Any]:
    """Build the unified error body for a status code with sensible fallbacks."""
    return {
        "error": {
            "code": code or DEFAULT_CODE_BY_STATUS.get(status_code, f"http_{status_code}"),
            "message": message or DEFAULT_MESSAGE_BY_STATUS.get(status_code, "Request failed."),
            "details": details,
        }
    }


def _split_detail(detail: Any) -> tuple[str | None, dict[str, Any] | list[Any] | None]:
    """Split an ``HTTPException.detail`` into (message, details).

    A dict detail with a ``"code"`` key is treated as a fully custom error payload:
    ``{"code": ..., "message": ..., "details": ...}`` (``message``/``details`` optional).
    A plain dict/list without ``"code"`` is treated as the ``details`` value.
    """
    if isinstance(detail, dict):
        if "code" in detail:
            message = detail.get("message")
            extra_details = detail.get("details")
            if extra_details is None:
                leftover = {k: v for k, v in detail.items() if k not in ("code", "message", "details")}
                extra_details = leftover or None
            return message, extra_details
        return None, detail
    if isinstance(detail, list):
        return None, detail
    if detail is None or (isinstance(detail, str) and not detail.strip()):
        return None, None
    return str(detail), None


def _validation_details(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalise Pydantic v2 error dicts into JSON-safe ``{loc, msg, type}`` items."""
    normalised: list[dict[str, Any]] = []
    for err in errors:
        normalised.append(
            {
                "loc": [str(part) for part in err.get("loc", [])],
                "msg": str(err.get("msg", "Invalid value.")),
                "type": str(err.get("type", "value_error")),
            }
        )
    return normalised


def _http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    message, details = _split_detail(exc.detail)
    code: str | None = None
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        code = str(exc.detail["code"])
    payload = _error_payload(exc.status_code, code=code, message=message, details=details)
    headers = getattr(exc, "headers", None)
    return JSONResponse(status_code=exc.status_code, content=payload, headers=headers)


def _request_validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    payload = _error_payload(
        422,
        code="validation_error",
        message="Request validation failed.",
        details=_validation_details(exc.errors()),
    )
    return JSONResponse(status_code=422, content=payload)


def _pydantic_validation_handler(request: Request, exc: ValidationError) -> JSONResponse:
    # A Pydantic ValidationError outside request parsing indicates a server-side bug.
    logger.error(
        "Response validation failed for %s %s",
        request.method,
        request.url.path,
        extra={"path": request.url.path, "validation_errors": _validation_details(exc.errors())},
        exc_info=exc,
    )
    payload = _error_payload(500, code="internal_error", message="An unexpected error occurred.")
    return JSONResponse(status_code=500, content=payload)


def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "Unhandled exception on %s %s",
        request.method,
        request.url.path,
        extra={"path": request.url.path, "error_type": type(exc).__name__},
        exc_info=exc,
    )
    payload = _error_payload(500, code="internal_error", message="An unexpected error occurred.")
    return JSONResponse(status_code=500, content=payload)


def register_exception_handlers(app: FastAPI) -> None:
    """Attach the unified error handlers to an application."""
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _request_validation_handler)
    app.add_exception_handler(ValidationError, _pydantic_validation_handler)
    app.add_exception_handler(Exception, _unhandled_exception_handler)
