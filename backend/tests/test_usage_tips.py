from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from contextlib import contextmanager

import pytest
from sqlalchemy import delete

from api_compass.db.session import apply_rls_scope, reset_rls_scope
from api_compass.models.enums import EnvironmentType, ProviderType
from api_compass.models.tables import Budget, DailyUsageCost, RawUsageEvent, Org
from api_compass.services import tips as tips_service


@contextmanager
def _scoped(session, org_id):
    apply_rls_scope(session, org_id)
    try:
        yield
    finally:
        reset_rls_scope(session)


@pytest.mark.usefixtures("apply_migrations")
def test_usage_tips_surface_when_conditions_met(db_session):
    org_id = uuid_setup_org(db_session)

    now = datetime.now(timezone.utc)
    samples = [
        RawUsageEvent(
            org_id=org_id,
            connection_id=None,
            provider=ProviderType.OPENAI,
            environment=EnvironmentType.PROD,
            metric="openai:tokens",
            unit="token",
            quantity=Decimal("100000"),
            unit_cost=Decimal("0.000002"),
            cost=Decimal("200"),
            currency="usd",
            ts=now - timedelta(days=1),
            source="test",
            metadata_json={"model": "gpt-4o", "requests": 20},
        ),
        RawUsageEvent(
            org_id=org_id,
            connection_id=None,
            provider=ProviderType.SENDGRID,
            environment=EnvironmentType.PROD,
            metric="sendgrid:emails_sent",
            unit="email",
            quantity=Decimal("5000"),
            unit_cost=Decimal("0.0006"),
            cost=Decimal("3"),
            currency="usd",
            ts=now - timedelta(days=1),
            source="test",
            metadata_json={"plan_consumed_percent": 85},
        ),
    ]
    db_session.add_all(samples)
    with _scoped(db_session, org_id):
        db_session.add(
            DailyUsageCost(
                org_id=org_id,
                provider=ProviderType.SENDGRID,
                environment=EnvironmentType.PROD,
                day=now.date(),
                quantity_sum=Decimal("0"),
                cost_sum=Decimal("50"),
                currency="usd",
            )
        )
        db_session.commit()
    with _scoped(db_session, org_id):
        db_session.add(
            Budget(
                org_id=org_id,
                provider=ProviderType.SENDGRID,
                environment=EnvironmentType.PROD,
                monthly_cap=Decimal("1000"),
                currency="usd",
            )
        )
        db_session.commit()

    tips = tips_service.get_usage_tips(db_session, org_id=org_id, environment=EnvironmentType.PROD)
    assert any("GPT-4" in tip.title or "GPT-4" in tip.body for tip in tips)
    assert any("SendGrid" in tip.title for tip in tips)

    from api_compass.models.tables import Org

    db_session.execute(delete(RawUsageEvent).where(RawUsageEvent.org_id == org_id))
    db_session.execute(delete(DailyUsageCost).where(DailyUsageCost.org_id == org_id))
    db_session.execute(delete(Budget).where(Budget.org_id == org_id))
    db_session.commit()
    db_session.execute(delete(Org).where(Org.id == org_id))
    db_session.commit()


def uuid_setup_org(db_session):
    org = Org(name="Tip Org")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    return org.id
