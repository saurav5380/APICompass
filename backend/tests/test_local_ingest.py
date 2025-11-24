from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select

from api_compass.db.session import apply_rls_scope, reset_rls_scope
from api_compass.models.tables import Connection, RawUsageEvent
from api_compass.services import local_agents


def _create_local_connection(client, headers) -> tuple[str, str]:
    payload = {
        "provider": "openai",
        "environment": "prod",
        "display_name": "OpenAI Local",
        "local_connector_enabled": True,
        "scopes": [],
    }
    resp = client.post("/connections", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    return data["id"], data["local_agent_token"]


def test_local_ingest_persists_usage(client, org_headers, db_session):
    headers, org_id = org_headers
    connection_id, agent_token = _create_local_connection(client, headers)
    ts = datetime.now(timezone.utc).isoformat()
    ingest_payload = {
        "connection_id": connection_id,
        "provider": "openai",
        "environment": "prod",
        "source": "local-agent",
        "agent_version": "local-connector/0.1.0",
        "samples": [
            {
                "metric": "openai:tokens",
                "unit": "token",
                "quantity": 12345,
                "unit_cost": "0.000002",
                "currency": "usd",
                "ts": ts,
                "metadata": {"requests": 42},
            }
        ],
    }
    body = json.dumps(ingest_payload).encode("utf-8")
    signature = local_agents.sign_payload(agent_token, body)
    resp = client.post(
        "/ingest/",
        data=body,
        headers={"Content-Type": "application/json", "X-Agent-Signature": signature},
    )
    assert resp.status_code == 202, resp.text
    assert resp.json()["ingested"] == 1

    apply_rls_scope(db_session, org_id)
    try:
        events = (
            db_session.execute(
                select(RawUsageEvent).where(RawUsageEvent.connection_id == UUID(connection_id))
            )
            .scalars()
            .all()
        )
        assert len(events) == 1
        assert events[0].metadata_json["agent_version"] == ingest_payload["agent_version"]
        assert events[0].source == "local-agent"

        connection = db_session.get(Connection, UUID(connection_id))
        assert connection is not None
        assert connection.local_agent_last_seen_at is not None
    finally:
        reset_rls_scope(db_session)
