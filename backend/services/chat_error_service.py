from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal

from observability import redact


SupportedLocale = Literal["en", "es"]
ERROR_PREFIX = "CHAT_ERROR:"


@dataclass(frozen=True)
class PublicChatError:
    code: str
    status_code: int
    retryable: bool
    messages: dict[SupportedLocale, str]

    def serialize(self, locale: SupportedLocale, request_id: str) -> str:
        return ERROR_PREFIX + json.dumps(
            {
                "code": self.code,
                "message": self.messages[locale],
                "retryable": self.retryable,
                "reference": request_id[:12],
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )


def _exception_summary(exc: Exception) -> str:
    parts: list[str] = []
    current: BaseException | None = exc
    visited: set[int] = set()
    while current is not None and id(current) not in visited:
        visited.add(id(current))
        parts.append(f"{type(current).__name__}: {redact(current)}")
        current = current.__cause__ or current.__context__
    return " | ".join(parts)[:1500]


def _status_code(exc: Exception) -> int | None:
    for candidate in (exc, exc.__cause__, exc.__context__):
        if candidate is None:
            continue
        value = getattr(candidate, "status_code", None) or getattr(candidate, "code", None)
        if isinstance(value, int):
            return value
        name = getattr(value, "name", "")
        if name == "RESOURCE_EXHAUSTED":
            return 429
        if name == "PERMISSION_DENIED":
            return 403
        if name == "UNAUTHENTICATED":
            return 401
    return None


def classify_chat_error(exc: Exception) -> PublicChatError:
    summary = _exception_summary(exc).lower()
    status_code = _status_code(exc)

    if any(
        phrase in summary
        for phrase in (
            "prepayment credits are depleted",
            "credits are depleted",
            "insufficient credit",
            "no available credit",
            "credit balance",
            "billing account",
            "payment required",
        )
    ):
        return PublicChatError(
            code="billing_unavailable",
            status_code=503,
            retryable=False,
            messages={
                "en": "Text chat is temporarily unavailable because the AI provider has no available credit.",
                "es": "El chat de texto no está disponible temporalmente porque el proveedor de IA no tiene crédito disponible.",
            },
        )

    if status_code == 401 or any(
        phrase in summary
        for phrase in (
            "api_key_invalid",
            "api key not valid",
            "invalid api key",
            "unauthenticated",
            "google_api_key is not configured",
        )
    ):
        return PublicChatError(
            code="provider_authentication_failed",
            status_code=503,
            retryable=False,
            messages={
                "en": "Text chat is temporarily unavailable because its AI connection is not configured correctly.",
                "es": "El chat de texto no está disponible temporalmente porque su conexión con la IA no está configurada correctamente.",
            },
        )

    if status_code == 429 or any(
        phrase in summary
        for phrase in ("quota", "rate limit", "resource exhausted", "resourceexhausted")
    ):
        return PublicChatError(
            code="provider_quota_exceeded",
            status_code=429,
            retryable=True,
            messages={
                "en": "The AI service is receiving too many requests. Please wait a moment and try again.",
                "es": "El servicio de IA está recibiendo demasiadas solicitudes. Espera un momento e inténtalo de nuevo.",
            },
        )

    if status_code == 403 or "permission denied" in summary:
        return PublicChatError(
            code="provider_access_denied",
            status_code=503,
            retryable=False,
            messages={
                "en": "Text chat is temporarily unavailable because the AI provider rejected its configuration.",
                "es": "El chat de texto no está disponible temporalmente porque el proveedor de IA rechazó su configuración.",
            },
        )

    if status_code in {408, 500, 502, 503, 504} or any(
        phrase in summary
        for phrase in ("timeout", "timed out", "deadline exceeded", "service unavailable")
    ):
        return PublicChatError(
            code="provider_temporarily_unavailable",
            status_code=503,
            retryable=True,
            messages={
                "en": "The AI service is temporarily unavailable. Please try again in a moment.",
                "es": "El servicio de IA no está disponible temporalmente. Inténtalo de nuevo en un momento.",
            },
        )

    return PublicChatError(
        code="chat_generation_failed",
        status_code=502,
        retryable=True,
        messages={
            "en": "Django could not complete the response. Please try again.",
            "es": "Django no pudo completar la respuesta. Inténtalo de nuevo.",
        },
    )


def diagnostic_summary(exc: Exception) -> str:
    return _exception_summary(exc)
