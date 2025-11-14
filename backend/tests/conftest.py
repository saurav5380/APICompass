from __future__ import annotations

import pytest
from pathlib import Path

from alembic import command
from alembic.config import Config as AlembicConfig
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
from sqlalchemy import delete, inspect, text

from api_compass.db.session import DATABASE_URL, SessionLocal, engine, apply_rls_scope, reset_rls_scope
from api_compass.main import app
from api_compass.models.tables import Budget, Connection, DailyUsageCost, Org


def _alembic_config() -> AlembicConfig:
    root_dir = Path(__file__).resolve().parents[1]
    config_path = root_dir / "alembic.ini"
    cfg = AlembicConfig(str(config_path))
    cfg.set_main_option("script_location", str(root_dir / "alembic"))
    cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
    return cfg


def _alembic_state(cfg: AlembicConfig) -> tuple[bool, str]:
    inspector = inspect(engine)
    script = ScriptDirectory.from_config(cfg)
    head = script.get_current_head()

    has_version = "alembic_version" in inspector.get_table_names()
    if not has_version:
        return False, head

    with engine.connect() as connection:
        current = connection.execute(text("SELECT version_num FROM alembic_version")).scalar()

    return current == head, head


@pytest.fixture(scope="session", autouse=True)
def apply_migrations() -> None:
    cfg = _alembic_config()
    at_head, head = _alembic_state(cfg)
    if at_head:
        return

    inspector = inspect(engine)
    if "alembic_version" not in inspector.get_table_names():
        command.stamp(cfg, head)
    else:
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

    apply_rls_scope(db_session, org.id)
    try:
        db_session.execute(delete(DailyUsageCost).where(DailyUsageCost.org_id == org.id))
        db_session.execute(delete(Connection).where(Connection.org_id == org.id))
        db_session.execute(delete(Budget).where(Budget.org_id == org.id))
        db_session.commit()
    finally:
        reset_rls_scope(db_session)

    db_session.execute(delete(Org).where(Org.id == org.id))
    db_session.commit()
