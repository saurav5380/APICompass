from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from api_compass.models.enums import EnvironmentType, ProviderType
from api_compass.models.tables import Budget


def test_create_budget(client, db_session, org_headers):
    headers, org_id = org_headers
    payload = {
        "provider": "openai",
        "environment": "prod",
        "monthly_cap": "2500",
        "currency": "usd",
    }

    response = client.post("/budgets/", headers=headers, json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["currency"] == "USD"
    assert data["provider"] == "openai"

    stored = db_session.execute(select(Budget).where(Budget.org_id == org_id)).scalar_one()
    assert stored.monthly_cap == Decimal("2500")


def test_upsert_budget_overwrites_existing(client, db_session, org_headers):
    headers, org_id = org_headers
    payload = {
        "provider": "sendgrid",
        "environment": "prod",
        "monthly_cap": "1000",
        "currency": "usd",
    }
    first = client.post("/budgets/", headers=headers, json=payload)
    assert first.status_code == 201

    payload["monthly_cap"] = "2000"
    second = client.post("/budgets/", headers=headers, json=payload)
    assert second.status_code == 201
    assert second.json()["monthly_cap"] == "2000.00"

    stored = db_session.execute(
        select(Budget).where(
            Budget.org_id == org_id,
            Budget.provider == ProviderType.SENDGRID,
            Budget.environment == EnvironmentType.PROD,
        )
    ).scalar_one()
    assert stored.monthly_cap == Decimal("2000")


def test_delete_budget(client, db_session, org_headers):
    headers, org_id = org_headers
    payload = {
        "provider": None,
        "environment": "prod",
        "monthly_cap": "3000",
        "currency": "usd",
    }
    response = client.post("/budgets/", headers=headers, json=payload)
    budget_id = response.json()["id"]

    delete_response = client.delete(f"/budgets/{budget_id}", headers=headers)
    assert delete_response.status_code == 204

    rows = db_session.execute(select(Budget).where(Budget.org_id == org_id)).scalars().all()
    assert rows == []


def test_rejects_invalid_currency(client, org_headers):
    headers, _ = org_headers
    payload = {
        "provider": None,
        "environment": "prod",
        "monthly_cap": "3000",
        "currency": "1234",
    }
    response = client.post("/budgets/", headers=headers, json=payload)
    assert response.status_code == 422
