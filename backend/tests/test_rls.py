from __future__ import annotations

from uuid import uuid4

import pytest
from psycopg import errors as pg_errors
from sqlalchemy import select
from sqlalchemy import exc as sa_exc

from api_compass.db.session import SessionLocal, apply_rls_scope
from api_compass.models.enums import ConnectionStatus, EnvironmentType, ProviderType
from api_compass.models.tables import Connection, Org


def _make_org_name(suffix: str) -> str:
    return f"Test RLS Org {suffix} {uuid4().hex[:6]}"


def test_rls_blocks_cross_org_access():
    session = SessionLocal()
    org1 = Org(name=_make_org_name("one"))
    org2 = Org(name=_make_org_name("two"))
    session.add_all([org1, org2])
    session.flush()
    org1_id = org1.id
    org2_id = org2.id
    session.commit()

    try:
        # Attempting to insert data for another org while scoped to org1 raises.
        apply_rls_scope(session, org1_id)
        rogue_connection = Connection(
            org_id=org2_id,
            provider=ProviderType.OPENAI,
            environment=EnvironmentType.PROD,
            status=ConnectionStatus.PENDING,
            encrypted_auth_blob=b"{}",
        )
        session.add(rogue_connection)

        with pytest.raises(sa_exc.ProgrammingError) as exc_info:
            session.commit()
        assert isinstance(exc_info.value.orig, pg_errors.InsufficientPrivilege)
        session.rollback()

        # Matching org scope succeeds and data becomes readable for that org only.
        apply_rls_scope(session, org2_id)
        allowed_connection = Connection(
            org_id=org2_id,
            provider=ProviderType.SENDGRID,
            environment=EnvironmentType.PROD,
            status=ConnectionStatus.ACTIVE,
            encrypted_auth_blob=b"{}",
        )
        session.add(allowed_connection)
        session.flush()
        allowed_connection_id = allowed_connection.id
        session.commit()

        apply_rls_scope(session, org1_id)
        rows = session.execute(
            select(Connection.id).where(Connection.id == allowed_connection_id)
        ).scalars().all()
        assert rows == []
    finally:
        session.close()
