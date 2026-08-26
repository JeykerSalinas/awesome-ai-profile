"""Explicit database setup: python -m scripts.init_contact_store. Sends no email."""
from sqlalchemy import create_engine

from settings import get_settings
from services.contact_store import initialize_contact_schema


if __name__ == "__main__":
    settings = get_settings()
    if not settings.contact_database_url:
        raise SystemExit("Configure CONTACT_DATABASE_URL first")
    engine = None
    try:
        engine = create_engine(settings.contact_database_url.get_secret_value(), hide_parameters=True)
        initialize_contact_schema(engine)
        print("Contact tables are ready. No email was sent.")
    except Exception:
        raise SystemExit("Contact database setup failed. Check database access.") from None
    finally:
        if engine is not None:
            engine.dispose()
