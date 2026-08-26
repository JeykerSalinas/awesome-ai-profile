"""Server-only opt-in. Missing settings or storage fail closed, never simulate success."""
from functools import lru_cache
from threading import Lock

from fastapi import HTTPException

from settings import get_settings
from services.contact_store import MemoryContactStore
from services.contact_email_service import EmailContactService
from services.resend_transport import ResendTransport, valid_sender


def email_configured(settings):
    return bool(settings.contact_email_enabled and settings.resend_api_key
            and settings.resend_api_key.get_secret_value().strip()
            and valid_sender(settings.contact_from_email))


def public_delivery_config():
    settings = get_settings()
    return {"mode": settings.contact_delivery_mode,
            "available": settings.contact_delivery_mode == "simulation" or email_configured(settings)}


@lru_cache
def _build_real_contact_service():
    settings = get_settings()
    if not email_configured(settings):
        raise HTTPException(503, "contact_unavailable")
    store = MemoryContactStore(settings.contact_daily_limit, settings.contact_sessions_per_hour,
                               settings.contact_max_sessions)
    return EmailContactService(store,
        ResendTransport(settings.resend_api_key.get_secret_value(), settings.contact_from_email))


_service_lock = Lock()


def real_contact_service():
    # lru_cache alone allows duplicate initial construction under concurrent calls.
    # One process must always use the same memory store, including its first requests.
    with _service_lock:
        return _build_real_contact_service()
