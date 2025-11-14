from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Iterable
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api_compass.models.enums import EnvironmentType, ProviderType
from api_compass.models.tables import Budget, DailyUsageCost, RawUsageEvent


@dataclass(slots=True)
class UsageTip:
    title: str
    body: str
    reason: str
    link: str


def get_usage_tips(session: Session, org_id: UUID, environment: EnvironmentType) -> list[UsageTip]:
    tips: list[UsageTip] = []
    window_end = datetime.now(timezone.utc)
    window_start = window_end - timedelta(days=7)

    openai_tip = _tip_high_gpt4_ratio(session, org_id, environment, window_start, window_end)
    if openai_tip:
        tips.append(openai_tip)

    duplicate_tip = _tip_duplicate_prompts(session, org_id, environment, window_start, window_end)
    if duplicate_tip:
        tips.append(duplicate_tip)

    sendgrid_tip = _tip_sendgrid_near_cap(session, org_id, environment)
    if sendgrid_tip:
        tips.append(sendgrid_tip)

    return tips


def _tip_high_gpt4_ratio(
    session: Session,
    org_id: UUID,
    environment: EnvironmentType,
    window_start: datetime,
    window_end: datetime,
) -> UsageTip | None:
    metadata_model = RawUsageEvent.metadata_json["model"].astext
    case_gpt4 = sa.case(
        (metadata_model.ilike("gpt-4%"), RawUsageEvent.quantity),
        else_=Decimal("0"),
    )

    stmt = (
        select(
            func.coalesce(func.sum(case_gpt4), Decimal("0")).label("gpt4_tokens"),
            func.coalesce(func.sum(RawUsageEvent.quantity), Decimal("0")).label("total_tokens"),
        )
        .where(RawUsageEvent.org_id == org_id)
        .where(RawUsageEvent.provider == ProviderType.OPENAI)
        .where(RawUsageEvent.environment == environment)
        .where(RawUsageEvent.ts >= window_start)
        .where(RawUsageEvent.ts <= window_end)
    )
    results = session.execute(stmt).one_or_none()
    if results is None:
        return None

    gpt4_tokens = Decimal(results.gpt4_tokens or 0)
    total_tokens = Decimal(results.total_tokens or 0)
    if total_tokens <= 0 or gpt4_tokens <= 0:
        return None
    ratio = gpt4_tokens / total_tokens
    if ratio < Decimal("0.6"):
        return None

    percent = round(float(ratio * 100), 1)
    reason = f"{percent}% of OpenAI tokens over the past week hit GPT-4 models."
    body = "Route non-critical prompts to GPT-4o mini or GPT-4.1 mini to trim per-request cost."
    link = "https://platform.openai.com/docs/guides/billing#optimize-model-choice"
    return UsageTip(
        title="High GPT-4 spend",
        body=body,
        reason=reason,
        link=link,
    )


def _tip_duplicate_prompts(
    session: Session,
    org_id: UUID,
    environment: EnvironmentType,
    window_start: datetime,
    window_end: datetime,
) -> UsageTip | None:
    requests_field = RawUsageEvent.metadata_json["requests"].astext.cast(sa.Numeric)
    stmt = (
        select(
            func.coalesce(func.sum(RawUsageEvent.quantity), Decimal("0")).label("tokens"),
            func.coalesce(func.sum(requests_field), Decimal("0")).label("requests"),
        )
        .where(RawUsageEvent.org_id == org_id)
        .where(RawUsageEvent.provider == ProviderType.OPENAI)
        .where(RawUsageEvent.environment == environment)
        .where(RawUsageEvent.ts >= window_start)
        .where(RawUsageEvent.ts <= window_end)
    )
    row = session.execute(stmt).one_or_none()
    if row is None:
        return None

    tokens = Decimal(row.tokens or 0)
    requests = Decimal(row.requests or 0)
    if tokens <= 0 or requests <= 0:
        return None

    expected_requests = tokens / Decimal("1000")
    if expected_requests <= 0:
        return None

    duplicate_ratio = max(Decimal("0"), (expected_requests - requests) / expected_requests)
    if duplicate_ratio < Decimal("0.3"):
        return None

    percent = round(float(duplicate_ratio * 100), 1)
    reason = f"Estimated duplicate prompts at {percent}% based on tokens vs. unique requests."
    body = "Cache embeddings/responses for repeated prompts to shave off repeated completions."
    link = "https://openai.com/blog/new-embedding-techniques#cache"
    return UsageTip(
        title="Cache duplicated prompts",
        body=body,
        reason=reason,
        link=link,
    )


def _tip_sendgrid_near_cap(
    session: Session,
    org_id: UUID,
    environment: EnvironmentType,
) -> UsageTip | None:
    stmt = (
        select(Budget, DailyUsageCost)
        .join(DailyUsageCost, DailyUsageCost.org_id == Budget.org_id)
        .where(Budget.org_id == org_id)
        .where(Budget.provider == ProviderType.SENDGRID)
        .where(Budget.environment == environment)
        .where(DailyUsageCost.provider == ProviderType.SENDGRID)
        .where(DailyUsageCost.environment == environment)
        .order_by(DailyUsageCost.day.desc())
        .limit(1)
    )
    row = session.execute(stmt).first()
    if not row:
        return None

    budget, latest = row
    plan_stmt = (
        select(
            RawUsageEvent.metadata_json["plan_consumed_percent"].astext.cast(sa.Numeric)
        )
        .where(RawUsageEvent.org_id == org_id)
        .where(RawUsageEvent.provider == ProviderType.SENDGRID)
        .where(RawUsageEvent.environment == environment)
        .order_by(RawUsageEvent.ts.desc())
        .limit(1)
    )
    plan_row = session.execute(plan_stmt).scalar_one_or_none()
    if plan_row is None:
        return None

    percent = Decimal(plan_row or 0)
    if percent < Decimal("75"):
        return None

    reason = f"SendGrid plan at {percent}% of quota while cap is {budget.monthly_cap} {budget.currency.upper()}."
    body = "Review email plan tiers or pause lower-value campaigns before overages kick in."
    link = "https://docs.sendgrid.com/ui/account-and-settings/usage-limits"
    return UsageTip(
        title="SendGrid nearing plan limit",
        body=body,
        reason=reason,
        link=link,
    )
