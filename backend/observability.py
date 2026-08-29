from __future__ import annotations

import json
import logging
import re
import sys
from datetime import UTC, datetime
from time import monotonic
from uuid import uuid4

from fastapi import FastAPI, Request, Response

from settings import get_settings


_STANDARD_LOG_RECORD_FIELDS = frozenset(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__
)
_REDACTION_PATTERNS = (
    re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
    re.compile(
        r"(?i)(api[-_ ]?key|authorization|token|secret)(\s*[:=]\s*)([^\s,;]+)"
    ),
)


def redact(value: object) -> str:
    text = " ".join(str(value).split())
    configured_key = get_settings().google_api_key
    if configured_key:
        text = text.replace(configured_key, "[REDACTED]")
    for pattern in _REDACTION_PATTERNS:
        if pattern.groups == 3:
            text = pattern.sub(r"\1\2[REDACTED]", text)
        else:
            text = pattern.sub("[REDACTED]", text)
    return text


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact(record.getMessage()),
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD_LOG_RECORD_FIELDS and not key.startswith("_"):
                payload[key] = redact(value) if isinstance(value, str) else value
        if record.exc_info:
            payload["exception"] = redact(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging() -> None:
    settings = get_settings()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(
        level=settings.log_level.upper(),
        handlers=[handler],
        force=True,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def install_request_logging(app: FastAPI) -> None:
    logger = logging.getLogger("http")

    @app.middleware("http")
    async def log_http_request(request: Request, call_next) -> Response:
        request_id = request.headers.get("x-request-id", "")
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", request_id):
            request_id = uuid4().hex
        request.state.request_id = request_id

        started = monotonic()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "http_request_failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round((monotonic() - started) * 1000),
                },
            )
            raise

        response.headers["X-Request-ID"] = request_id
        logger.info(
            "http_request_completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round((monotonic() - started) * 1000),
            },
        )
        return response
