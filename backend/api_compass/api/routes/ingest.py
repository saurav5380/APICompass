from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from api_compass.api.deps import get_system_session
from api_compass.models.enums import ConnectionStatus
from api_compass.models.tables import Connection
from api_compass.schemas.ingest import LocalUsageIngest
from api_compass.services import entitlements as entitlement_service
from api_compass.services import local_agents, usage as usage_service

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("/", status_code=status.HTTP_202_ACCEPTED)
async def ingest_usage(
    request: Request,
    x_agent_signature: str | None = Header(default=None, alias="X-Agent-Signature"),
    session: Session = Depends(get_system_session),
) -> dict[str, int]:
    raw_body = await request.body()
    payload = LocalUsageIngest.model_validate_json(raw_body)

    connection = session.get(Connection, payload.connection_id)
    if connection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found.")
    if not connection.local_connector_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Connection is not configured for Local Connector mode.",
        )
    if connection.status != ConnectionStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Connection is not active.")
    if connection.provider != payload.provider or connection.environment != payload.environment:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payload scope mismatch.")

    agent_token = local_agents.extract_agent_token(connection.encrypted_auth_blob)
    if agent_token is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Agent token is missing.")
    if not local_agents.verify_signature(agent_token, x_agent_signature, raw_body):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Local Connector signature.")

    snapshot = entitlement_service.get_entitlements(session, connection.org_id)
    now = datetime.now(timezone.utc)
    if not entitlement_service.allow_sync(snapshot, connection.last_synced_at, now):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Sync interval has not elapsed for this connection.",
        )

    samples: list[usage_service.UsageSample] = []
    for sample in payload.samples:
        metadata = dict(sample.metadata or {})
        metadata["agent_version"] = payload.agent_version
        usage_sample = usage_service.UsageSample(
            org_id=connection.org_id,
            connection_id=connection.id,
            provider=payload.provider,
            environment=payload.environment,
            metric=sample.metric,
            unit=sample.unit,
            quantity=sample.quantity,
            unit_cost=sample.unit_cost,
            currency=sample.currency,
            ts=sample.ts,
            source=payload.source,
            metadata=metadata,
        )
        samples.append(usage_sample)

    created = usage_service.save_usage_samples(session, samples)
    last_ts = max((sample.ts for sample in samples), default=now)
    connection.last_synced_at = last_ts
    connection.local_agent_last_seen_at = now
    session.add(connection)
    session.commit()
    return {"ingested": created}
