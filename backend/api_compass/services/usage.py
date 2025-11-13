from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from hashlib import sha256
from typing import Any, Iterable
from uuid import UUID, uuid5

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from api_compass.models.enums import EnvironmentType, ProviderType
from api_compass.models.tables import Connection, DailyUsageCost, RawUsageEvent

USAGE_EVENT_NAMESPACE = UUID("f4e8b4a0-9bd3-4f16-9930-49f9f1469ef8")


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
            index_elements=["org_id", "provider", "environment", "day"],
            set_={
                "quantity_sum": DailyUsageCost.quantity_sum + sample.quantity,
                "cost_sum": DailyUsageCost.cost_sum + cost_value,
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
