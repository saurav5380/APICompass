from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.orm import Session

from api_compass.models.enums import ConnectionStatus
from api_compass.models.tables import Connection
from api_compass.schemas.connections import ConnectionCreate, ConnectionRead
from api_compass.services import jobs
from api_compass.utils.crypto import encrypt_auth_payload, mask_secret


def _minimal_scopes(scopes: Iterable[str]) -> list[str]:
    normalized = {scope.strip().lower() for scope in scopes if scope and scope.strip()}
    return sorted(normalized) or ["basic"]


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _build_response(connection: Connection) -> ConnectionRead:
    metadata = connection.metadata_json or {}
    return ConnectionRead(
        id=connection.id,
        provider=connection.provider,
        environment=connection.environment,
        display_name=connection.display_name,
        status=connection.status,
        scopes=connection.scopes or [],
        masked_key=metadata.get("masked_preview", "****"),
        created_at=connection.created_at,
        last_synced_at=connection.last_synced_at,
    )


def create_connection(session: Session, org_id: UUID, payload: ConnectionCreate) -> ConnectionRead:
    secret = payload.api_key.get_secret_value()
    encrypted_auth = encrypt_auth_payload(
        {
            "api_key": secret,
            "provider": payload.provider,
            "captured_at": _now_iso(),
        }
    )
    metadata = {
        "masked_preview": mask_secret(secret),
        "scopes_version": "minimal",
    }

    connection = Connection(
        org_id=org_id,
        provider=payload.provider,
        environment=payload.environment,
        status=ConnectionStatus.ACTIVE,
        display_name=payload.display_name,
        encrypted_auth_blob=encrypted_auth,
        scopes=_minimal_scopes(payload.scopes or []),
        metadata_json=metadata,
    )

    session.add(connection)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise

    session.refresh(connection)
    jobs.schedule_sync(connection.id)
    return _build_response(connection)


def list_connections(session: Session, org_id: UUID) -> list[ConnectionRead]:
    result = session.execute(
        select(Connection)
        .where(Connection.org_id == org_id)
        .order_by(Connection.created_at.desc())
    )
    connections = result.scalars().all()
    return [_build_response(connection) for connection in connections]


def revoke_connection(session: Session, org_id: UUID, connection_id: UUID) -> ConnectionRead:
    result = session.execute(
        select(Connection).where(Connection.org_id == org_id, Connection.id == connection_id).with_for_update()
    )
    connection = result.scalars().first()
    if connection is None:
        raise NoResultFound

    connection.status = ConnectionStatus.DISABLED
    connection.encrypted_auth_blob = b""
    metadata = connection.metadata_json or {}
    metadata.update({"revoked_at": _now_iso()})
    connection.metadata_json = metadata

    session.add(connection)
    session.commit()
    session.refresh(connection)

    jobs.cancel_scheduled_jobs(connection.id)
    return _build_response(connection)
