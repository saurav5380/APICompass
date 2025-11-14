from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import delete

from api_compass.db.session import apply_rls_scope, reset_rls_scope
from api_compass.models.enums import EnvironmentType, ProviderType
from api_compass.models.tables import Budget, DailyUsageCost, Org
from api_compass.services import usage as usage_service


def _seed_daily_costs(session, org_id, provider, environment, start_day, values):
    apply_rls_scope(session, org_id)
    try:
        for idx, value in enumerate(values):
            session.add(
                DailyUsageCost(
                    org_id=org_id,
                    provider=provider,
                    environment=environment,
                    day=start_day + timedelta(days=idx),
                    quantity_sum=Decimal("0"),
                    cost_sum=Decimal(value),
                    currency="usd",
                )
            )
        session.commit()
    finally:
        reset_rls_scope(session)


def test_usage_projection_service(db_session):
    org = Org(name="Usage Projection Org")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)

    budget = Budget(
        org_id=org.id,
        provider=ProviderType.OPENAI,
        environment=EnvironmentType.PROD,
        monthly_cap=Decimal("5000"),
        currency="usd",
    )
    db_session.add(budget)
    db_session.commit()

    today = date.today()
    month_start = today.replace(day=1)
    values = [100 + idx * 10 for idx in range(10)]  # increasing trend
    _seed_daily_costs(
        db_session,
        org_id=org.id,
        provider=ProviderType.OPENAI,
        environment=EnvironmentType.PROD,
        start_day=month_start,
        values=values,
    )

    projections = usage_service.get_usage_projections(
        session=db_session,
        org_id=org.id,
        environment=EnvironmentType.PROD,
        provider=ProviderType.OPENAI,
    )
    assert projections, "expected projection data"
    summary = projections[0]
    assert summary.projected_total >= summary.month_to_date
    assert summary.projected_min <= summary.projected_total <= summary.projected_max
    assert summary.rolling_avg_7d is not None
    assert summary.rolling_avg_14d is not None
    assert summary.budget_limit == Decimal("5000.00")
    assert summary.budget_source == "provider"

    db_session.execute(delete(DailyUsageCost).where(DailyUsageCost.org_id == org.id))
    db_session.execute(delete(Budget).where(Budget.org_id == org.id))
    db_session.execute(delete(Org).where(Org.id == org.id))
    db_session.commit()


@pytest.mark.usefixtures("apply_migrations")
def test_usage_projection_endpoint(client, db_session, org_headers):
    headers, org_id = org_headers
    today = date.today()
    month_start = today.replace(day=1)
    values = [80 + idx * 5 for idx in range(8)]
    _seed_daily_costs(
        db_session,
        org_id=org_id,
        provider=ProviderType.TWILIO,
        environment=EnvironmentType.PROD,
        start_day=month_start,
        values=values,
    )

    db_session.add(
        Budget(
            org_id=org_id,
            provider=None,
            environment=EnvironmentType.PROD,
            monthly_cap=Decimal("4000"),
            currency="usd",
        )
    )
    db_session.commit()

    response = client.get("/usage/projections", headers=headers, params={"environment": "prod"})
    assert response.status_code == 200
    payload = response.json()
    assert payload, "should return projections"
    projection = next(item for item in payload if item["provider"] == "twilio")
    assert Decimal(projection["projected_total"]) >= Decimal(projection["month_to_date_spend"])
    assert projection["tooltip"].startswith("Projection blends")
    assert projection["budget_limit"] == "4000.00"
    assert projection["budget_source"] == "org"

    db_session.execute(delete(DailyUsageCost).where(DailyUsageCost.org_id == org_id))
    db_session.execute(delete(Budget).where(Budget.org_id == org_id))
    db_session.commit()
