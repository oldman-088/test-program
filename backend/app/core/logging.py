"""Structured JSON logging for the whole application.

Every log record is emitted as a single JSON object on stdout::

    {"timestamp": "2026-11-26T12:34:56.789Z", "level": "INFO", "logger": "app.api.health",
     "message": "...", "exception": "...", ...extra fields}

Additional keyword data should be passed through ``logger.info("...", extra={"key": value})``;
any non-reserved record attribute is serialised into the payload.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime

_JSON_HANDLER_ATTR = "_aatm_json_handler"

# Attributes of logging.LogRecord that are not user-supplied "extra" fields.
_RESERVED_ATTRS = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "stackLevel",
        "thread",
        "threadName",
        "taskName",
        "task",
    }
)


class JsonFormatter(logging.Formatter):
    """Serialise log records as one-line JSON objects with UTC ISO-8601 timestamps."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED_ATTRS and not key.startswith("_"):
                try:
                    json.dumps(value)
                except (TypeError, ValueError):
                    payload[key] = repr(value)
                else:
                    payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def _resolve_level(level: str) -> int:
    resolved = logging.getLevelName(level.strip().upper())
    if isinstance(resolved, int):
        return resolved
    logging.getLogger(__name__).warning("Unknown LOG_LEVEL %r; falling back to INFO", level)
    return logging.INFO


def configure_logging(level: str = "INFO") -> None:
    """Install the JSON handler on the root logger exactly once and set the level.

    Uvicorn's own loggers are re-pointed at the root handler so the process emits a
    single, structured stream. Safe to call repeatedly (e.g. once per test/app factory).
    """
    root = logging.getLogger()
    existing: logging.Handler | None = getattr(root, _JSON_HANDLER_ATTR, None)
    if existing is None:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        handler.set_name("aatm-json")
        root.addHandler(handler)
        setattr(root, _JSON_HANDLER_ATTR, handler)
    root.setLevel(_resolve_level(level))

    # Fold uvicorn's loggers into the root JSON handler.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uv_logger = logging.getLogger(name)
        uv_logger.handlers = []
        uv_logger.propagate = True
