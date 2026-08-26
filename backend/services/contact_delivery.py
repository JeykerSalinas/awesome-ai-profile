"""Server-only opt-in. Missing settings or storage fail closed, never simulate success."""
from functools import lru_cache

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

from settings import get_settings
from services.contact_store import PersistentContactService
from services.resend_transport import ResendTransport, valid_sender


def email_configured(settings):
    if not (settings.contact_email_enabled and settings.resend_api_key
            and settings.resend_api_key.get_secret_value().strip()
            and valid_sender(settings.contact_from_email) and settings.contact_database_url):
        return False
    try:
        return make_url(settings.contact_database_url.get_secret_value()).drivername == "postgresql+psycopg"
    except Exception:
        return False


def public_delivery_config():
    settings = get_settings()
    return {"mode": settings.contact_delivery_mode,
            "available": settings.contact_delivery_mode == "simulation" or email_configured(settings)}


@lru_cache
def real_contact_service():
    settings = get_settings()
    if not email_configured(settings):
        raise HTTPException(503, "contact_unavailable")
    engine = create_engine(settings.contact_database_url.get_secret_value(), pool_pre_ping=True,
                           connect_args={"connect_timeout": 5}, hide_parameters=True)
    return PersistentContactService(engine,
        ResendTransport(settings.resend_api_key.get_secret_value(), settings.contact_from_email),
        settings.contact_daily_limit, settings.contact_sessions_per_hour)
