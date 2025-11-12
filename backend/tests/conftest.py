from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from api_compass.db.session import SessionLocal
from api_compass.main import app
from api_compass.models.tables import Connection, Org


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

    db_session.execute(delete(Connection).where(Connection.org_id == org.id))
    db_session.execute(delete(Org).where(Org.id == org.id))
    db_session.commit()
