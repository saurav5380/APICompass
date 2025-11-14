from __future__ import annotations

import pytest
from pathlib import Path

from alembic import command
from alembic.config import Config as AlembicConfig
from fastapi.testclient import TestClient
from sqlalchemy import delete

from api_compass.db.session import DATABASE_URL, SessionLocal
from api_compass.main import app
from api_compass.models.tables import Budget, Connection, DailyUsageCost, Org


def _alembic_config() -> AlembicConfig:
    root_dir = Path(__file__).resolve().parents[1]
    config_path = root_dir / "alembic.ini"
    cfg = AlembicConfig(str(config_path))
    cfg.set_main_option("script_location", str(root_dir / "alembic"))
    cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
    return cfg


@pytest.fixture(scope="session", autouse=True)
def apply_migrations() -> None:
    cfg = _alembic_config()
    command.upgrade(cfg, "head")


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def org_headers(db_session):
    org = Org(name="Test Org Connections")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)

    yield {"X-Org-Id": str(org.id)}, org.id

    db_session.execute(delete(DailyUsageCost).where(DailyUsageCost.org_id == org.id))
    db_session.execute(delete(Connection).where(Connection.org_id == org.id))
    db_session.execute(delete(Budget).where(Budget.org_id == org.id))
    db_session.execute(delete(Org).where(Org.id == org.id))
    db_session.commit()
