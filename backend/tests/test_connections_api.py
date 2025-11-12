from __future__ import annotations

from uuid import UUID

from api_compass.services.jobs import cancellation_key, redis_client


def test_connections_crud_flow(client, org_headers):
    headers, _ = org_headers
    api_key = "sk-live-test-1234567890"
    payload = {
        "provider": "openai",
        "environment": "prod",
        "display_name": "OpenAI Primary",
        "api_key": api_key,
        "scopes": ["completions:read"],
    }

    create_resp = client.post("/connections", json=payload, headers=headers)
    assert create_resp.status_code == 201, create_resp.text
    created = create_resp.json()
    assert created["provider"] == "openai"
    assert created["masked_key"].endswith(api_key[-4:])
    connection_id = created["id"]

    list_resp = client.get("/connections", headers=headers)
    assert list_resp.status_code == 200
    listed = list_resp.json()
    assert len(listed) == 1
    assert listed[0]["id"] == connection_id
    assert listed[0]["masked_key"].endswith(api_key[-4:])

    delete_resp = client.delete(f"/connections/{connection_id}", headers=headers)
    assert delete_resp.status_code == 200
    revoked = delete_resp.json()
    assert revoked["status"] == "disabled"

    r = redis_client()
    key = cancellation_key(UUID(connection_id))
    ttl = r.ttl(key)
    assert ttl is not None and ttl > 0 and ttl <= 60
    r.delete(key)
