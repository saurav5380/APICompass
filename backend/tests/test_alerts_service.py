from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import delete, select, func

from api_compass.models.enums import EnvironmentType, ProviderType
from api_compass.models.tables import AlertEvent, Budget, DailyUsageCost, Org
from api_compass.services import alerts as alert_service


def _add_daily_costs(session, org_id, provider, environment, start_day, values):
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


@pytest.mark.usefixtures("apply_migrations")
def test_over_cap_alert_triggers_once(db_session):
    org = Org(name="Alert Test Org")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)

    budget = Budget(
        org_id=org.id,
        provider=ProviderType.OPENAI,
        environment=EnvironmentType.PROD,
        monthly_cap=Decimal("1000"),
        currency="usd",
        threshold_percent=80,
    )
    db_session.add(budget)
    db_session.commit()

    month_start = date.today().replace(day=1)
    _add_daily_costs(
        db_session,
        org_id=org.id,
        provider=ProviderType.OPENAI,
        environment=EnvironmentType.PROD,
        start_day=month_start,
        values=[200, 250, 300, 350, 400],
    )

    alert_service.evaluate_alerts_for_org(org.id)
    count = db_session.execute(select(func.count(AlertEvent.id))).scalar_one()
    assert count == 1

    alert_service.evaluate_alerts_for_org(org.id)
    count_after = db_session.execute(select(func.count(AlertEvent.id))).scalar_one()
    assert count_after == 1

    db_session.execute(delete(AlertEvent))
    db_session.execute(delete(DailyUsageCost))
    db_session.execute(delete(Budget))
    db_session.execute(delete(Org))
    db_session.commit()


@pytest.mark.usefixtures("apply_migrations")
def test_daily_digest_records_event(db_session):
    org = Org(name="Digest Org")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)

    yesterday = date.today() - timedelta(days=1)
    db_session.add(
        DailyUsageCost(
            org_id=org.id,
            provider=ProviderType.TWILIO,
            environment=EnvironmentType.PROD,
            day=yesterday,
            quantity_sum=Decimal("0"),
            cost_sum=Decimal("123.45"),
            currency="usd",
        )
    )
    db_session.commit()

    alert_service.send_daily_digest_for_org(org.id, target_day=yesterday)
    events = db_session.execute(select(AlertEvent).where(AlertEvent.alert_type == "daily_digest")).scalars().all()
    assert len(events) == 1

    db_session.execute(delete(AlertEvent))
    db_session.execute(delete(DailyUsageCost))
    db_session.execute(delete(Org))
    db_session.commit()
