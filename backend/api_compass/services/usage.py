from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
import time
from typing import Any, Iterable, Sequence
from uuid import UUID, uuid5

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from api_compass.db.session import engine
from api_compass.models.enums import EnvironmentType, ProviderType
from api_compass.models.tables import Connection, DailyUsageCost, RawUsageEvent

USAGE_EVENT_NAMESPACE = UUID("f4e8b4a0-9bd3-4f16-9930-49f9f1469ef8")
MONEY_QUANT = Decimal("0.01")
PROJECTION_TOOLTIP = (
    "Projection blends the 7-day and 14-day rolling averages with a short-term linear trend. "
    "The confidence range comes from the variance of the recent 14-day window."
)


@dataclass(slots=True, frozen=True)
class UsageSample:
    org_id: UUID
    connection_id: UUID | None
    provider: ProviderType
    environment: EnvironmentType
    metric: str
    unit: str
    quantity: Decimal
    unit_cost: Decimal | None
    currency: str
    ts: datetime
    source: str
    metadata: dict[str, Any] | None = None

    @property
    def cost(self) -> Decimal | None:
        if self.unit_cost is None:
            return None
        return (self.quantity * self.unit_cost).quantize(Decimal("0.000001"))


def _stable_event_id(sample: UsageSample) -> UUID:
    token = f"{sample.provider.value}:{sample.connection_id or sample.org_id}:{sample.metric}:{sample.ts.isoformat()}"
    return uuid5(USAGE_EVENT_NAMESPACE, token)


def save_usage_samples(session: Session, samples: Iterable[UsageSample]) -> int:
    saved = 0
    for sample in samples:
        event_id = _stable_event_id(sample)
        payload = {
            "id": event_id,
            "org_id": sample.org_id,
            "connection_id": sample.connection_id,
            "provider": sample.provider,
            "environment": sample.environment,
            "metric": sample.metric,
            "unit": sample.unit,
            "quantity": sample.quantity,
            "unit_cost": sample.unit_cost,
            "cost": sample.cost,
            "currency": sample.currency,
            "ts": sample.ts,
            "source": sample.source,
            "metadata_json": sample.metadata,
        }
        stmt = (
            insert(RawUsageEvent)
            .values(**payload)
            .on_conflict_do_nothing(index_elements=["id", "ts"])
        )
        result = session.execute(stmt)
        if result.rowcount == 0:
            continue

        saved += 1
        _upsert_daily_cost(session, sample)
    return saved


def _upsert_daily_cost(session: Session, sample: UsageSample) -> None:
    day = sample.ts.date()
    cost_value = sample.cost or Decimal("0")
    stmt = (
        insert(DailyUsageCost)
        .values(
            org_id=sample.org_id,
            provider=sample.provider,
            environment=sample.environment,
            day=day,
            quantity_sum=sample.quantity,
            cost_sum=cost_value,
            currency=sample.currency,
        )
        .on_conflict_do_update(
            constraint="uq_daily_usage_scope",
            set_={
                "quantity_sum": DailyUsageCost.quantity_sum + sample.quantity,
                "cost_sum": DailyUsageCost.cost_sum + cost_value,
                "currency": sample.currency,
            },
        )
    )
    session.execute(stmt)


def month_to_date_spend(
    session: Session, org_id: UUID, provider: ProviderType, environment: EnvironmentType
) -> Decimal:
    today = date.today()
    start = today.replace(day=1)
    result = session.execute(
        select(func.coalesce(func.sum(DailyUsageCost.cost_sum), 0))
        .where(DailyUsageCost.org_id == org_id)
        .where(DailyUsageCost.provider == provider)
        .where(DailyUsageCost.environment == environment)
        .where(DailyUsageCost.day >= start)
    )
    return result.scalar_one()


def describe_samples(samples: Iterable[UsageSample]) -> dict[str, Any]:
    metrics: dict[str, str] = {}
    total_cost = Decimal("0")
    for sample in samples:
        metrics[sample.metric] = f"{sample.quantity} {sample.unit}"
        if sample.cost is not None:
            total_cost += sample.cost
    return {"metrics": metrics, "total_cost": total_cost}


def _daily_quantity(connection: Connection, metric: str, minimum: int, maximum: int, *, ts: datetime) -> Decimal:
    if minimum >= maximum:
        raise ValueError("minimum must be less than maximum")
    seed = f"{connection.id}:{metric}:{ts.date().isoformat()}"
    digest = int(sha256(seed.encode("utf-8")).hexdigest(), 16)
    value = minimum + (digest % (maximum - minimum + 1))
    return Decimal(value)


def openai_usage_samples(connection: Connection, ts: datetime) -> list[UsageSample]:
    prompt_tokens = _daily_quantity(connection, "openai_prompt_tokens", 150_000, 750_000, ts=ts)
    completion_tokens = _daily_quantity(connection, "openai_completion_tokens", 80_000, 600_000, ts=ts)
    unit_cost = Decimal("0.000002")
    metadata = {
        "model": "gpt-4o-mini",
        "requests": int((prompt_tokens + completion_tokens) // 1000),
        "month_to_date_tokens": int(prompt_tokens + completion_tokens),
    }
    sample = UsageSample(
        org_id=connection.org_id,
        connection_id=connection.id,
        provider=connection.provider,
        environment=connection.environment,
        metric="openai:tokens",
        unit="token",
        quantity=prompt_tokens + completion_tokens,
        unit_cost=unit_cost,
        currency="usd",
        ts=ts,
        source="poll-openai",
        metadata=metadata,
    )
    return [sample]


def twilio_usage_samples(connection: Connection, ts: datetime) -> list[UsageSample]:
    sms_segments = _daily_quantity(connection, "twilio_sms_segments", 150, 2500, ts=ts)
    voice_minutes = _daily_quantity(connection, "twilio_voice_minutes", 25, 480, ts=ts)
    sms_sample = UsageSample(
        org_id=connection.org_id,
        connection_id=connection.id,
        provider=connection.provider,
        environment=connection.environment,
        metric="twilio:sms_segments",
        unit="segment",
        quantity=sms_segments,
        unit_cost=Decimal("0.0075"),
        currency="usd",
        ts=ts,
        source="poll-twilio",
        metadata={"product": "sms", "messages": int(sms_segments)},
    )
    voice_sample = UsageSample(
        org_id=connection.org_id,
        connection_id=connection.id,
        provider=connection.provider,
        environment=connection.environment,
        metric="twilio:voice_minutes",
        unit="minute",
        quantity=voice_minutes,
        unit_cost=Decimal("0.015"),
        currency="usd",
        ts=ts,
        source="poll-twilio",
        metadata={"product": "voice", "calls": int(voice_minutes // 5)},
    )
    return [sms_sample, voice_sample]


def sendgrid_usage_samples(connection: Connection, ts: datetime) -> list[UsageSample]:
    raw_quota = (connection.metadata_json or {}).get("plan_quota", 100_000)
    try:
        plan_quota = int(raw_quota)
    except (TypeError, ValueError):
        plan_quota = 100_000
    emails_sent = _daily_quantity(connection, "sendgrid_emails", 1_000, 8_000, ts=ts)
    total_sent = Decimal(min(plan_quota, int(emails_sent)))
    percent = round((float(total_sent) / float(plan_quota)) * 100, 2) if plan_quota else 0
    metadata = {
        "plan_quota": plan_quota,
        "plan_consumed_percent": percent,
        "deliveries": int(emails_sent * Decimal("0.97")),
        "bounces": int(emails_sent * Decimal("0.01")),
    }
    sample = UsageSample(
        org_id=connection.org_id,
        connection_id=connection.id,
        provider=connection.provider,
        environment=connection.environment,
        metric="sendgrid:emails_sent",
        unit="email",
        quantity=emails_sent,
        unit_cost=Decimal("0.0006"),
        currency="usd",
        ts=ts,
        source="poll-sendgrid",
        metadata=metadata,
    )
    return [sample]


PROVIDER_GENERATORS: dict[ProviderType, Any] = {
    ProviderType.OPENAI: openai_usage_samples,
    ProviderType.TWILIO: twilio_usage_samples,
    ProviderType.SENDGRID: sendgrid_usage_samples,
}


def build_provider_samples(connection: Connection, ts: datetime) -> list[UsageSample]:
    generator = PROVIDER_GENERATORS.get(connection.provider)
    if generator is None:
        return []
    return generator(connection, ts)


def refresh_daily_usage_costs(days: int, *, max_seconds: int, chunk_days: int = 5) -> dict[str, Any]:
    if days <= 0:
        raise ValueError("days must be positive")

    chunk_days = max(1, min(chunk_days, days))
    chunk = timedelta(days=chunk_days)
    window_count = 0
    start_time = time.monotonic()
    end_ts = datetime.now(timezone.utc)
    start_ts = end_ts - timedelta(days=days)

    upsert_sql = text(
        """
        INSERT INTO daily_usage_costs (org_id, provider, environment, day, quantity_sum, cost_sum, currency)
        SELECT
            org_id,
            provider,
            environment,
            date_trunc('day', ts)::date AS day,
            COALESCE(SUM(quantity), 0)::numeric(20, 6) AS quantity_sum,
            COALESCE(SUM(cost), 0)::numeric(20, 6) AS cost_sum,
            MAX(currency) AS currency
        FROM raw_usage_events
        WHERE ts >= :start AND ts < :end
        GROUP BY org_id, provider, environment, day
        ON CONFLICT (org_id, provider, environment, day)
        DO UPDATE SET
            quantity_sum = EXCLUDED.quantity_sum,
            cost_sum = EXCLUDED.cost_sum,
            currency = EXCLUDED.currency
        """
    )

    with engine.begin() as conn:
        window_start = start_ts
        while window_start < end_ts:
            window_end = min(window_start + chunk, end_ts)
            conn.execute(upsert_sql, {"start": window_start, "end": window_end})
            window_count += 1
            window_start = window_end
            elapsed = time.monotonic() - start_time
            if elapsed > max_seconds:
                raise TimeoutError(
                    f"Daily usage backfill exceeded {max_seconds}s after {elapsed:.2f}s"
                )

    duration = time.monotonic() - start_time
    return {
        "windows": window_count,
        "duration_seconds": duration,
        "range_start": start_ts.isoformat(),
        "range_end": end_ts.isoformat(),
    }


@dataclass(slots=True)
class ProjectionSummary:
    provider: ProviderType
    environment: EnvironmentType
    currency: str
    month_to_date: Decimal
    projected_total: Decimal
    projected_min: Decimal
    projected_max: Decimal
    rolling_avg_7d: Decimal | None
    rolling_avg_14d: Decimal | None
    sample_days: int
    tooltip: str = PROJECTION_TOOLTIP


def get_usage_projections(
    session: Session,
    org_id: UUID,
    environment: EnvironmentType,
    provider: ProviderType | None = None,
) -> list[ProjectionSummary]:
    today = datetime.now(timezone.utc).date()
    month_start = today.replace(day=1)
    days_elapsed = (today - month_start).days + 1
    days_in_month = monthrange(today.year, today.month)[1]

    if days_elapsed <= 0:
        return []

    query = (
        select(
            DailyUsageCost.provider,
            DailyUsageCost.day,
            DailyUsageCost.cost_sum,
            DailyUsageCost.currency,
        )
        .where(DailyUsageCost.org_id == org_id)
        .where(DailyUsageCost.environment == environment)
        .where(DailyUsageCost.day >= month_start)
        .where(DailyUsageCost.day <= today)
    )

    if provider:
        query = query.where(DailyUsageCost.provider == provider)

    rows = session.execute(query).all()
    if not rows and provider is None:
        return []

    grouped: dict[ProviderType, dict[str, Any]] = {}
    for prov, day, cost_sum, currency in rows:
        bucket = grouped.setdefault(
            prov,
            {
                "currency": currency or "usd",
                "days": {},
            },
        )
        bucket["days"][day] = Decimal(cost_sum or 0)

    # Ensure we include the requested provider even if no data yet.
    if provider and provider not in grouped:
        grouped[provider] = {"currency": "usd", "days": {}}

    summaries: list[ProjectionSummary] = []
    for prov, payload in grouped.items():
        day_map: dict[date, Decimal] = payload["days"]
        series = _build_daily_series(day_map, month_start, days_elapsed)
        summary = _build_projection_for_series(
            provider=prov,
            environment=environment,
            currency=payload["currency"],
            daily_series=series,
            days_in_month=days_in_month,
            today=today,
        )
        summaries.append(summary)

    # Sort by provider name for deterministic responses.
    summaries.sort(key=lambda item: item.provider.value)
    return summaries


def _build_daily_series(day_map: dict[date, Decimal], month_start: date, days_elapsed: int) -> list[Decimal]:
    series = [Decimal("0")] * days_elapsed
    for day, cost in day_map.items():
        index = (day - month_start).days
        if 0 <= index < days_elapsed:
            series[index] = Decimal(cost)
    return series


def _build_projection_for_series(
    provider: ProviderType,
    environment: EnvironmentType,
    currency: str,
    daily_series: Sequence[Decimal],
    days_in_month: int,
    today: date,
) -> ProjectionSummary:
    month_to_date = sum(daily_series, start=Decimal("0"))
    avg_7 = _rolling_average(daily_series, 7)
    avg_14 = _rolling_average(daily_series, 14)

    remaining_days = max(days_in_month - len(daily_series), 0)
    avg_projection = Decimal("0")
    if remaining_days > 0:
        avg_candidates = [avg for avg in (avg_7, avg_14) if avg is not None]
        if avg_candidates:
            avg_recent = sum(avg_candidates, start=Decimal("0")) / Decimal(len(avg_candidates))
            avg_projection = avg_recent * Decimal(remaining_days)

    linear_projection = _linear_projection(daily_series, days_in_month)

    projected_remaining = Decimal("0")
    non_zero_components = [component for component in (avg_projection, linear_projection) if component > 0]
    if len(non_zero_components) == 2:
        projected_remaining = sum(non_zero_components, start=Decimal("0")) / Decimal(2)
    elif non_zero_components:
        projected_remaining = non_zero_components[0]

    projected_total = month_to_date + projected_remaining
    band = _confidence_band(daily_series, remaining_days)
    projected_min = max(projected_total - band, Decimal("0"))
    projected_max = projected_total + band

    return ProjectionSummary(
        provider=provider,
        environment=environment,
        currency=currency or "usd",
        month_to_date=_quantize_money(month_to_date),
        projected_total=_quantize_money(projected_total),
        projected_min=_quantize_money(projected_min),
        projected_max=_quantize_money(projected_max),
        rolling_avg_7d=_quantize_money(avg_7) if avg_7 is not None else None,
        rolling_avg_14d=_quantize_money(avg_14) if avg_14 is not None else None,
        sample_days=len(daily_series),
    )


def _rolling_average(series: Sequence[Decimal], window: int) -> Decimal | None:
    if not series:
        return None
    if len(series) < window:
        if len(series) == 0:
            return None
        window_values = series
    else:
        window_values = series[-window:]

    total = sum(window_values, start=Decimal("0"))
    count = len(window_values)
    if count == 0:
        return None
    return total / Decimal(count)


def _linear_projection(series: Sequence[Decimal], days_in_month: int) -> Decimal:
    n = len(series)
    if n == 0:
        return Decimal("0")

    x_vals = [Decimal(index) for index in range(1, n + 1)]
    y_vals = [Decimal(value) for value in series]
    x_mean = sum(x_vals, start=Decimal("0")) / Decimal(n)
    y_mean = sum(y_vals, start=Decimal("0")) / Decimal(n)

    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_vals, y_vals))
    denominator = sum((x - x_mean) ** 2 for x in x_vals)
    slope = numerator / denominator if denominator != 0 else Decimal("0")
    intercept = y_mean - slope * x_mean

    projected = Decimal("0")
    for idx in range(n + 1, days_in_month + 1):
        day_value = slope * Decimal(idx) + intercept
        projected += max(day_value, Decimal("0"))
    return projected


def _confidence_band(series: Sequence[Decimal], remaining_days: int) -> Decimal:
    if remaining_days <= 0 or not series:
        return Decimal("0")
    window_size = min(len(series), 14)
    window = series[-window_size:]
    if len(window) < 2:
        return Decimal("0")
    mean = sum(window, start=Decimal("0")) / Decimal(len(window))
    variance = sum((value - mean) ** 2 for value in window) / Decimal(len(window) - 1)
    if variance == 0:
        return Decimal("0")
    std_dev = variance.sqrt()
    return std_dev * Decimal(remaining_days).sqrt()


def _quantize_money(value: Decimal | None) -> Decimal:
    if value is None:
        return Decimal("0").quantize(MONEY_QUANT)
    return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
