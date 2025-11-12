from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api_compass.core.config import settings

DATABASE_URL = str(settings.database_url)

engine = create_engine(DATABASE_URL, echo=False, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
