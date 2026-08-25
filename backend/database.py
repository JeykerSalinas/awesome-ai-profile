from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from settings import get_settings

settings = get_settings()
engine = create_engine(settings.database_url)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)
from sqlalchemy import text

with engine.connect() as connection:
    result = connection.execute(text("SELECT 1"))
    print(result.scalar())