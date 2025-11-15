from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from api_compass.models.enums import PlanType


@dataclass(frozen=True)
class PlanDefinition:
    plan: PlanType
    label: str
    description: str
    max_providers: int
    sync_interval_minutes: int
    digest_frequency: str
    alerts_enabled: bool
    tips_enabled: bool
    stripe_lookup_key: str | None = None
    unit_amount_cents: int | None = None
    trial_days: int | None = None


PLAN_DEFINITIONS: Final[dict[PlanType, PlanDefinition]] = {
    PlanType.FREE: PlanDefinition(
        plan=PlanType.FREE,
        label="Free",
        description="Monitor a single provider with daily syncs and weekly digests.",
        max_providers=1,
        sync_interval_minutes=24 * 60,
        digest_frequency="weekly",
        alerts_enabled=False,
        tips_enabled=False,
        stripe_lookup_key=None,
        unit_amount_cents=None,
        trial_days=None,
    ),
    PlanType.PRO: PlanDefinition(
        plan=PlanType.PRO,
        label="Pro",
        description="Unlock hourly syncs, multi-provider coverage, alerts, and tips.",
        max_providers=3,
        sync_interval_minutes=60,
        digest_frequency="daily",
        alerts_enabled=True,
        tips_enabled=True,
        stripe_lookup_key="api-compass-pro-monthly",
        unit_amount_cents=9900,
        trial_days=14,
    ),
    PlanType.ENTERPRISE: PlanDefinition(
        plan=PlanType.ENTERPRISE,
        label="Enterprise",
        description="Custom entitlements negotiated via sales.",
        max_providers=10,
        sync_interval_minutes=15,
        digest_frequency="daily",
        alerts_enabled=True,
        tips_enabled=True,
        stripe_lookup_key=None,
        unit_amount_cents=None,
        trial_days=None,
    ),
}

PLAN_LOOKUP_BY_KEY: Final[dict[str, PlanDefinition]] = {
    definition.stripe_lookup_key: definition
    for definition in PLAN_DEFINITIONS.values()
    if definition.stripe_lookup_key
}


def get_plan_definition(plan: PlanType) -> PlanDefinition:
    return PLAN_DEFINITIONS.get(plan, PLAN_DEFINITIONS[PlanType.FREE])


def plan_from_lookup_key(lookup_key: str | None) -> PlanDefinition | None:
    if not lookup_key:
        return None
    return PLAN_LOOKUP_BY_KEY.get(lookup_key)


__all__ = [
    "PlanDefinition",
    "PLAN_DEFINITIONS",
    "PLAN_LOOKUP_BY_KEY",
    "get_plan_definition",
    "plan_from_lookup_key",
]
