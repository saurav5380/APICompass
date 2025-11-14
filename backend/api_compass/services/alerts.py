from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api_compass.core.config import settings
from api_compass.db.session import SessionLocal
from api_compass.models import (
    AlertChannel,
    AlertEvent,
    AlertSeverity,
    Budget,
    DailyUsageCost,
    Org,
    ProviderType,
)
from api_compass.models.enums import EnvironmentType
from api_compass.services import notifications, usage

logger = logging.getLogger(__name__)


class AlertType(str):
    OVER_CAP = "over_cap"
    NEAR_CAP = "near_cap"
    SPIKE = "spike"
    DIGEST = "daily_digest"


@dataclass(slots=True)
class AlertCandidate:
    alert_type: str
    severity: AlertSeverity
    provider: ProviderType | None
    environment: EnvironmentType
    budget_id: UUID | None
    message: str
    metadata: dict[str, str]


def evaluate_all_orgs() -> None:
    with SessionLocal() as session:
        org_ids = session.execute(select(Org.id)).scalars().all()

    for org_id in org_ids:
        try:
            evaluate_alerts_for_org(org_id)
        except Exception:
            logger.exception("Alert evaluation failed for org %s", org_id)


def evaluate_alerts_for_org(org_id: UUID) -> None:
    with SessionLocal() as session:
        budgets = session.execute(select(Budget).where(Budget.org_id == org_id)).scalars().all()
        if not budgets:
            return

        envs = {budget.environment or EnvironmentType.PROD for budget in budgets}
        projections_cache: dict[tuple[EnvironmentType, ProviderType], usage.ProjectionSummary] = {}
        aggregated_cache: dict[EnvironmentType, usage.ProjectionSummary] = {}

        for env in envs:
            summaries = usage.get_usage_projections(session, org_id=org_id, environment=env)
            for summary in summaries:
                projections_cache[(env, summary.provider)] = summary
            if summaries:
                aggregated_cache[env] = _aggregate_summaries(env, summaries)

        for budget in budgets:
            environment = budget.environment or EnvironmentType.PROD
            summary = (
                projections_cache.get((environment, budget.provider))
                if budget.provider
                else aggregated_cache.get(environment)
            )
            if summary is None:
                continue
            candidates = _build_candidates_for_budget(budget, summary, session)
            for candidate in candidates:
                _emit_alert_event(session, org_id, candidate)


def send_daily_digests() -> None:
    yesterday = date.today() - timedelta(days=1)
    with SessionLocal() as session:
        org_ids = session.execute(select(Org.id)).scalars().all()

    for org_id in org_ids:
        try:
            send_daily_digest_for_org(org_id, target_day=yesterday)
        except Exception:
            logger.exception("Daily digest failed for org %s", org_id)


def send_daily_digest_for_org(org_id: UUID, target_day: date | None = None) -> None:
    day = target_day or (date.today() - timedelta(days=1))
    with SessionLocal() as session:
        existing = _recent_event(
            session=session,
            org_id=org_id,
            alert_type=AlertType.DIGEST,
            provider=None,
            environment=None,
            budget_id=None,
            within=timedelta(hours=23),
        )
        if existing:
            return

        rows = session.execute(
            select(DailyUsageCost.provider, DailyUsageCost.environment, DailyUsageCost.cost_sum)
            .where(DailyUsageCost.org_id == org_id)
            .where(DailyUsageCost.day == day)
        ).all()

        if not rows:
            return

        lines = [f"Daily usage summary for {day.isoformat()}:"]
        totals = Decimal("0")
        currency = "USD"
        for provider, environment, cost in rows:
            env_label = (environment or EnvironmentType.PROD).value
            provider_label = provider.value if provider else "all-providers"
            amount = Decimal(cost or 0)
            totals += amount
            lines.append(f"- {provider_label} ({env_label}): ${amount:,.2f}")

        lines.append(f"Total: ${totals:,.2f}")
        candidate = AlertCandidate(
            alert_type=AlertType.DIGEST,
            severity=AlertSeverity.INFO,
            provider=None,
            environment=EnvironmentType.PROD,
            budget_id=None,
            message="\n".join(lines),
            metadata={"day": day.isoformat()},
        )

        _emit_alert_event(session, org_id, candidate, enforce_quiet_hours=False)


def _build_candidates_for_budget(
    budget: Budget,
    summary: usage.ProjectionSummary,
    session: Session,
) -> list[AlertCandidate]:
    candidates: list[AlertCandidate] = []
    cap = Decimal(budget.monthly_cap)
    provider = summary.provider if budget.provider else None
    environment = summary.environment

    if summary.projected_total > cap:
        message = (
            f"{provider.value if provider else 'All providers'} ({environment.value}) projected "
            f"to reach {summary.projected_total} against cap {cap}."
        )
        candidates.append(
            AlertCandidate(
                alert_type=AlertType.OVER_CAP,
                severity=AlertSeverity.CRITICAL,
                provider=provider,
                environment=environment,
                budget_id=budget.id,
                message=message,
                metadata={"projected_total": str(summary.projected_total), "cap": str(cap)},
            )
        )

    threshold = (cap * Decimal(budget.threshold_percent) / Decimal("100")).quantize(Decimal("0.01"))
    if summary.projected_total >= threshold and summary.projected_total <= cap:
        message = (
            f"{provider.value if provider else 'All providers'} ({environment.value}) forecast "
            f"{summary.projected_total} which is above the {budget.threshold_percent}% tier ({threshold})."
        )
        candidates.append(
            AlertCandidate(
                alert_type=AlertType.NEAR_CAP,
                severity=AlertSeverity.WARNING,
                provider=provider,
                environment=environment,
                budget_id=budget.id,
                message=message,
                metadata={"projected_total": str(summary.projected_total), "tier_threshold": str(threshold)},
            )
        )

    if _detect_spike(session, budget.org_id, provider, environment):
        message = (
            f"{provider.value if provider else 'All providers'} ({environment.value}) "
            "reported an unusual spike compared to the 14-day baseline."
        )
        candidates.append(
            AlertCandidate(
                alert_type=AlertType.SPIKE,
                severity=AlertSeverity.WARNING,
                provider=provider,
                environment=environment,
                budget_id=budget.id,
                message=message,
                metadata={},
            )
        )

    return candidates


def _detect_spike(
    session: Session,
    org_id: UUID,
    provider: ProviderType | None,
    environment: EnvironmentType,
) -> bool:
    window_days = 15
    base_stmt = (
        select(DailyUsageCost.day, DailyUsageCost.cost_sum)
        .where(DailyUsageCost.org_id == org_id)
        .where(DailyUsageCost.environment == environment)
        .order_by(DailyUsageCost.day.desc())
    )
    if provider:
        stmt = base_stmt.where(DailyUsageCost.provider == provider).limit(window_days)
    else:
        stmt = (
            select(DailyUsageCost.day, func.sum(DailyUsageCost.cost_sum))
            .where(DailyUsageCost.org_id == org_id)
            .where(DailyUsageCost.environment == environment)
            .group_by(DailyUsageCost.day)
            .order_by(DailyUsageCost.day.desc())
            .limit(window_days)
        )

    rows = session.execute(stmt).all()
    if len(rows) < 2:
        return False

    rows = list(reversed(rows))
    latest_day, latest_value = rows[-1]
    baseline_values = [Decimal(cost or 0) for _, cost in rows[:-1] if cost is not None]
    if not baseline_values:
        return False

    baseline_avg = sum(baseline_values, start=Decimal("0")) / Decimal(len(baseline_values))
    if baseline_avg == 0:
        return False

    latest_amount = Decimal(latest_value or 0)
    if latest_amount < Decimal(settings.alerts_spike_minimum):
        return False

    multiplier = Decimal(settings.alerts_spike_multiplier)
    return latest_amount >= baseline_avg * multiplier


def _emit_alert_event(
    session: Session,
    org_id: UUID,
    candidate: AlertCandidate,
    *,
    enforce_quiet_hours: bool = True,
) -> None:
    now = datetime.now(timezone.utc)
    if enforce_quiet_hours and _within_quiet_hours(now.time()):
        logger.info("Quiet hours active; skipping alert %s for org %s", candidate.alert_type, org_id)
        return

    within = timedelta(minutes=settings.alerts_debounce_minutes)
    if _recent_event(
        session,
        org_id=org_id,
        alert_type=candidate.alert_type,
        provider=candidate.provider,
        environment=candidate.environment,
        budget_id=candidate.budget_id,
        within=within,
    ):
        return

    event = AlertEvent(
        org_id=org_id,
        budget_id=candidate.budget_id,
        provider=candidate.provider,
        environment=candidate.environment,
        alert_type=candidate.alert_type,
        channel=AlertChannel.EMAIL,
        severity=candidate.severity,
        message=candidate.message,
        metadata_json=candidate.metadata,
    )
    session.add(event)
    session.commit()

    provider_label = candidate.provider.value if candidate.provider else "All providers"
    subject = f"[API Compass] {provider_label} {candidate.alert_type.replace('_', ' ').title()}"
    body = candidate.message
    notifications.send_email_alert(subject, body)


def _recent_event(
    session: Session,
    org_id: UUID,
    alert_type: str,
    provider: ProviderType | None,
    environment: EnvironmentType | None,
    budget_id: UUID | None,
    within: timedelta,
) -> AlertEvent | None:
    window_start = datetime.now(timezone.utc) - within
    stmt = (
        select(AlertEvent)
        .where(AlertEvent.org_id == org_id)
        .where(AlertEvent.alert_type == alert_type)
        .where(AlertEvent.channel == AlertChannel.EMAIL)
        .where(AlertEvent.triggered_at >= window_start)
        .order_by(AlertEvent.triggered_at.desc())
    )
    if provider is not None:
        stmt = stmt.where(AlertEvent.provider == provider)
    else:
        stmt = stmt.where(AlertEvent.provider.is_(None))

    if environment is not None:
        stmt = stmt.where(AlertEvent.environment == environment)
    else:
        stmt = stmt.where(AlertEvent.environment.is_(None))

    if budget_id is not None:
        stmt = stmt.where(AlertEvent.budget_id == budget_id)
    else:
        stmt = stmt.where(AlertEvent.budget_id.is_(None))

    return session.execute(stmt).scalar_one_or_none()


def _within_quiet_hours(current: time) -> bool:
    start = _parse_time(settings.alerts_quiet_hours_start)
    end = _parse_time(settings.alerts_quiet_hours_end)
    if start == end:
        return False
    if start < end:
        return start <= current < end
    return current >= start or current < end


def _parse_time(value: str) -> time:
    hour, minute = value.split(":")
    return time(hour=int(hour), minute=int(minute))


def _aggregate_summaries(
    environment: EnvironmentType,
    summaries: Sequence[usage.ProjectionSummary],
) -> usage.ProjectionSummary:
    total_mtd = sum((summary.month_to_date for summary in summaries), start=Decimal("0"))
    total_projected = sum((summary.projected_total for summary in summaries), start=Decimal("0"))
    total_min = sum((summary.projected_min for summary in summaries), start=Decimal("0"))
    total_max = sum((summary.projected_max for summary in summaries), start=Decimal("0"))
    avg7 = (
        sum((summary.rolling_avg_7d or Decimal("0") for summary in summaries), start=Decimal("0"))
        / Decimal(len(summaries))
    )
    avg14 = (
        sum((summary.rolling_avg_14d or Decimal("0") for summary in summaries), start=Decimal("0"))
        / Decimal(len(summaries))
    )
    currency = summaries[0].currency

    return usage.ProjectionSummary(
        provider=ProviderType.GENERIC,
        environment=environment,
        currency=currency,
        month_to_date=total_mtd,
        projected_total=total_projected,
        projected_min=total_min,
        projected_max=total_max,
        rolling_avg_7d=avg7,
        rolling_avg_14d=avg14,
        sample_days=max(summary.sample_days for summary in summaries),
        budget_limit=None,
        budget_remaining=None,
        budget_gap=None,
        budget_consumed_percent=None,
        budget_source=None,
        over_budget=False,
    )
