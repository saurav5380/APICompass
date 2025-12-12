from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Iterable
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from api_compass.models.enums import ProviderType
from api_compass.models.tables import DailyUsageCost, RawUsageEvent
from api_compass.schemas.metrics import MetricsOverview, MetricsTrendPoint


def _normalize_range(start: date | None, end: date | None) -> tuple[date, date]:
    today = date.today()
    default_start = today - timedelta(days=6)
    normalized_start = start or default_start
    normalized_end = end or today
    if normalized_start > normalized_end:
        normalized_start, normalized_end = normalized_end, normalized_start
    return normalized_start, normalized_end


def get_overview(
    session: Session,
    org_id: UUID,
    start_date: date | None = None,
    end_date: date | None = None,
    provider: ProviderType | None = None,
) -> MetricsOverview:
    start, end = _normalize_range(start_date, end_date)

    calls_stmt = (
        select(func.count(RawUsageEvent.id))
        .where(RawUsageEvent.org_id == org_id)
        .where(RawUsageEvent.ts >= start)
        .where(RawUsageEvent.ts < end + timedelta(days=1))
    )
    if provider:
        calls_stmt = calls_stmt.where(RawUsageEvent.provider == provider)
    total_calls = session.execute(calls_stmt).scalar_one()

    errors_stmt = (
        select(
            func.coalesce(
                func.sum(
                    case(
                        (RawUsageEvent.metric.ilike("%error%"), 1),
                        else_=0,
                    )
                ),
                0,
            )
        )
        .where(RawUsageEvent.org_id == org_id)
        .where(RawUsageEvent.ts >= start)
        .where(RawUsageEvent.ts < end + timedelta(days=1))
    )
    if provider:
        errors_stmt = errors_stmt.where(RawUsageEvent.provider == provider)
    total_errors = session.execute(errors_stmt).scalar_one()

    spend_stmt = (
        select(func.coalesce(func.sum(DailyUsageCost.cost_sum), 0))
        .where(DailyUsageCost.org_id == org_id)
        .where(DailyUsageCost.day >= start)
        .where(DailyUsageCost.day <= end)
    )
    if provider:
        spend_stmt = spend_stmt.where(DailyUsageCost.provider == provider)
    total_spend = session.execute(spend_stmt).scalar_one()

    return MetricsOverview(
        start_date=start,
        end_date=end,
        provider=provider,
        total_calls=int(total_calls or 0),
        total_errors=int(total_errors or 0),
        total_spend=total_spend if isinstance(total_spend, Decimal) else Decimal(total_spend or 0),
    )


def get_trends(
    session: Session,
    org_id: UUID,
    start_date: date | None = None,
    end_date: date | None = None,
    provider: ProviderType | None = None,
) -> list[MetricsTrendPoint]:
    start, end = _normalize_range(start_date, end_date)

    day_expr = func.date(RawUsageEvent.ts)
    events_stmt = (
        select(
            day_expr.label("day"),
            func.count(RawUsageEvent.id).label("calls"),
            func.coalesce(
                func.sum(
                    case(
                        (RawUsageEvent.metric.ilike("%error%"), 1),
                        else_=0,
                    )
                ),
                0,
            ).label("errors"),
        )
        .where(RawUsageEvent.org_id == org_id)
        .where(RawUsageEvent.ts >= start)
        .where(RawUsageEvent.ts < end + timedelta(days=1))
        .group_by(day_expr)
    )
    if provider:
        events_stmt = events_stmt.where(RawUsageEvent.provider == provider)

    event_rows: Iterable[tuple[date, int, int]] = session.execute(events_stmt).all()

    cost_stmt = (
        select(DailyUsageCost.day, func.sum(DailyUsageCost.cost_sum))
        .where(DailyUsageCost.org_id == org_id)
        .where(DailyUsageCost.day >= start)
        .where(DailyUsageCost.day <= end)
        .group_by(DailyUsageCost.day)
    )
    if provider:
        cost_stmt = cost_stmt.where(DailyUsageCost.provider == provider)

    cost_rows: Iterable[tuple[date, Decimal]] = session.execute(cost_stmt).all()

    trend_map: dict[date, dict[str, Decimal | int]] = {}
    for day, calls, errors in event_rows:
        trend_map[day] = trend_map.get(day, {"calls": 0, "errors": 0, "spend": Decimal(0)})
        trend_map[day]["calls"] = int(calls or 0)
        trend_map[day]["errors"] = int(errors or 0)
    for day, spend in cost_rows:
        trend_map[day] = trend_map.get(day, {"calls": 0, "errors": 0, "spend": Decimal(0)})
        trend_map[day]["spend"] = spend if isinstance(spend, Decimal) else Decimal(spend or 0)

    # Ensure empty days are included
    current = start
    results: list[MetricsTrendPoint] = []
    while current <= end:
        entry = trend_map.get(current, {"calls": 0, "errors": 0, "spend": Decimal(0)})
        results.append(
            MetricsTrendPoint(
                day=current,
                calls=int(entry["calls"]),
                errors=int(entry["errors"]),
                spend=entry["spend"],
            )
        )
        current += timedelta(days=1)

    return results
