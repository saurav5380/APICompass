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
from api_compass.services import audit
from api_compass.services import entitlements as entitlement_service
from api_compass.services import jobs
from api_compass.services import local_agents
from api_compass.utils.crypto import encrypt_auth_payload, mask_secret


def _minimal_scopes(scopes: Iterable[str]) -> list[str]:
    normalized = {scope.strip().lower() for scope in scopes if scope and scope.strip()}
    return sorted(normalized) or ["basic"]


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _build_response(connection: Connection, agent_token: str | None = None) -> ConnectionRead:
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
        local_connector_enabled=bool(connection.local_connector_enabled),
        local_agent_last_seen_at=connection.local_agent_last_seen_at,
        local_agent_token=agent_token,
    )


def create_connection(session: Session, org_id: UUID, payload: ConnectionCreate) -> ConnectionRead:
    entitlement_service.ensure_connection_slot(session, org_id)
    metadata = {"scopes_version": "minimal"}
    agent_token: str | None = None

    if payload.local_connector_enabled:
        agent_token = local_agents.generate_agent_token()
        encrypted_auth = local_agents.build_auth_blob(agent_token)
        metadata.update(
            {
                "masked_preview": local_agents.token_preview(agent_token),
                "local_mode": True,
            }
        )
    else:
        if payload.api_key is None:
            raise ValueError("api_key is required when local connector mode is disabled.")
        secret = payload.api_key.get_secret_value()
        encrypted_auth = encrypt_auth_payload(
            {
                "api_key": secret,
                "provider": payload.provider,
                "captured_at": _now_iso(),
            }
        )
        metadata.update(
            {
                "masked_preview": mask_secret(secret),
                "local_mode": False,
            }
        )

    connection = Connection(
        org_id=org_id,
        provider=payload.provider,
        environment=payload.environment,
        status=ConnectionStatus.ACTIVE,
        display_name=payload.display_name,
        encrypted_auth_blob=encrypted_auth,
        scopes=_minimal_scopes(payload.scopes or []),
        metadata_json=metadata,
        local_connector_enabled=payload.local_connector_enabled,
    )

    session.add(connection)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise

    session.refresh(connection)
    audit.log_action(
        session,
        org_id=org_id,
        action="connection.created",
        object_type="connection",
        object_id=str(connection.id),
        metadata={"provider": connection.provider.value, "environment": connection.environment.value},
    )
    if not payload.local_connector_enabled:
        jobs.schedule_sync(connection.id)
    return _build_response(connection, agent_token=agent_token)


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
    connection.local_connector_enabled = False

    session.add(connection)
    session.commit()
    session.refresh(connection)

    audit.log_action(
        session,
        org_id=org_id,
        action="connection.revoked",
        object_type="connection",
        object_id=str(connection.id),
        metadata={"provider": connection.provider.value, "environment": connection.environment.value},
    )
    jobs.cancel_scheduled_jobs(connection.id)
    return _build_response(connection)
