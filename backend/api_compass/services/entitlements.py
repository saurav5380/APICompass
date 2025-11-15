from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api_compass.core.plans import get_plan_definition, plan_from_lookup_key
from api_compass.models.enums import ConnectionStatus, PlanType
from api_compass.models.tables import Connection, Org, OrgEntitlement

TRIAL_STATUSES = {"trialing", "incomplete"}


class EntitlementError(Exception):
    """Base error for entitlement enforcement."""


class PlanLimitError(EntitlementError):
    def __init__(self, limit: int) -> None:
        super().__init__(f"Plan limit reached. Max providers: {limit}.")
        self.limit = limit


class FeatureDisabledError(EntitlementError):
    def __init__(self, feature: str) -> None:
        super().__init__(f"Feature '{feature}' is unavailable on the current plan.")
        self.feature = feature


@dataclass(slots=True)
class FeatureSnapshot:
    plan: PlanType
    max_providers: int
    sync_interval_minutes: int
    digest_frequency: str
    alerts_enabled: bool
    tips_enabled: bool
    trial_ends_at: datetime | None
    stripe_status: str

    @property
    def trial_active(self) -> bool:
        if not self.trial_ends_at:
            return False
        if self.stripe_status not in TRIAL_STATUSES:
            return False
        return self.trial_ends_at > datetime.now(timezone.utc)


def _ensure_entitlement(session: Session, org_id: UUID) -> OrgEntitlement:
    entitlement = session.execute(
        select(OrgEntitlement).where(OrgEntitlement.org_id == org_id)
    ).scalar_one_or_none()
    if entitlement:
        return entitlement

    org = session.get(Org, org_id)
    plan = org.plan if org and org.plan else PlanType.FREE
    definition = get_plan_definition(plan)
    entitlement = OrgEntitlement(
        org_id=org_id,
        plan=plan,
        max_providers=definition.max_providers,
        sync_interval_minutes=definition.sync_interval_minutes,
        digest_frequency=definition.digest_frequency,
        alerts_enabled=definition.alerts_enabled,
        tips_enabled=definition.tips_enabled,
        stripe_status="inactive",
    )
    session.add(entitlement)
    session.commit()
    session.refresh(entitlement)
    return entitlement


def _to_snapshot(entitlement: OrgEntitlement) -> FeatureSnapshot:
    return FeatureSnapshot(
        plan=entitlement.plan,
        max_providers=entitlement.max_providers,
        sync_interval_minutes=entitlement.sync_interval_minutes,
        digest_frequency=entitlement.digest_frequency,
        alerts_enabled=bool(entitlement.alerts_enabled),
        tips_enabled=bool(entitlement.tips_enabled),
        trial_ends_at=entitlement.trial_ends_at,
        stripe_status=entitlement.stripe_status or "inactive",
    )


def get_entitlements(session: Session, org_id: UUID) -> FeatureSnapshot:
    entitlement = _ensure_entitlement(session, org_id)
    return _to_snapshot(entitlement)


def build_feature_flags(snapshot: FeatureSnapshot) -> dict[str, Any]:
    return {
        "plan": snapshot.plan,
        "max_providers": snapshot.max_providers,
        "sync_interval_minutes": snapshot.sync_interval_minutes,
        "digest_frequency": snapshot.digest_frequency,
        "alerts_enabled": snapshot.alerts_enabled,
        "tips_enabled": snapshot.tips_enabled,
        "trial": {
            "active": snapshot.trial_active,
            "ends_at": snapshot.trial_ends_at,
        },
        "stripe_status": snapshot.stripe_status,
    }


def ensure_connection_slot(session: Session, org_id: UUID) -> FeatureSnapshot:
    snapshot = get_entitlements(session, org_id)
    active_connections = session.execute(
        select(func.count())
        .select_from(Connection)
        .where(Connection.org_id == org_id)
        .where(Connection.status == ConnectionStatus.ACTIVE)
    ).scalar_one()
    if active_connections >= snapshot.max_providers:
        raise PlanLimitError(snapshot.max_providers)
    return snapshot


def ensure_feature_enabled(snapshot: FeatureSnapshot, feature: str) -> None:
    if feature == "alerts" and not snapshot.alerts_enabled:
        raise FeatureDisabledError(feature)
    if feature == "tips" and not snapshot.tips_enabled:
        raise FeatureDisabledError(feature)


def _apply_definition(entitlement: OrgEntitlement, plan: PlanType) -> None:
    definition = get_plan_definition(plan)
    entitlement.plan = plan
    entitlement.max_providers = definition.max_providers
    entitlement.sync_interval_minutes = definition.sync_interval_minutes
    entitlement.digest_frequency = definition.digest_frequency
    entitlement.alerts_enabled = definition.alerts_enabled
    entitlement.tips_enabled = definition.tips_enabled


def apply_plan(
    session: Session,
    org_id: UUID,
    plan: PlanType,
    *,
    trial_ends_at: datetime | None = None,
    stripe_subscription_id: str | None = None,
    stripe_price_id: str | None = None,
    stripe_status: str | None = None,
) -> FeatureSnapshot:
    entitlement = _ensure_entitlement(session, org_id)
    _apply_definition(entitlement, plan)
    entitlement.trial_ends_at = trial_ends_at
    entitlement.stripe_subscription_id = stripe_subscription_id
    entitlement.stripe_price_id = stripe_price_id
    if stripe_status:
        entitlement.stripe_status = stripe_status
    session.add(entitlement)

    org = session.get(Org, org_id)
    if org:
        org.plan = plan
        session.add(org)

    session.commit()
    session.refresh(entitlement)
    return _to_snapshot(entitlement)


def handle_stripe_event(session: Session, event: dict[str, Any]) -> bool:
    event_type = event.get("type")
    data = event.get("data", {}).get("object")
    if not data:
        return False

    if event_type in {"customer.subscription.created", "customer.subscription.updated"}:
        return _sync_subscription(session, data)
    if event_type == "customer.subscription.deleted":
        return _cancel_subscription(session, data)
    return False


def _org_from_customer(session: Session, customer_id: str | None) -> Org | None:
    if not customer_id:
        return None
    return session.execute(select(Org).where(Org.stripe_customer_id == customer_id)).scalar_one_or_none()


def _first_price(subscription: dict[str, Any]) -> dict[str, Any] | None:
    items = subscription.get("items", {}).get("data") or []
    if not items:
        return None
    return items[0].get("price")


def _sync_subscription(session: Session, subscription: dict[str, Any]) -> bool:
    org = _org_from_customer(session, subscription.get("customer"))
    if not org:
        return False

    price = _first_price(subscription)
    definition = plan_from_lookup_key(price.get("lookup_key") if price else None)
    plan = definition.plan if definition else (org.plan or PlanType.FREE)

    trial_end = subscription.get("trial_end")
    trial_ends_at = (
        datetime.fromtimestamp(trial_end, tz=timezone.utc)
        if isinstance(trial_end, (int, float))
        else None
    )

    apply_plan(
        session=session,
        org_id=org.id,
        plan=plan,
        trial_ends_at=trial_ends_at,
        stripe_subscription_id=subscription.get("id"),
        stripe_price_id=price.get("id") if price else None,
        stripe_status=subscription.get("status"),
    )
    return True


def _cancel_subscription(session: Session, subscription: dict[str, Any]) -> bool:
    org = _org_from_customer(session, subscription.get("customer"))
    if not org:
        return False

    apply_plan(
        session=session,
        org_id=org.id,
        plan=PlanType.FREE,
        trial_ends_at=None,
        stripe_subscription_id=None,
        stripe_price_id=None,
        stripe_status="canceled",
    )
    return True


def expire_trials(session: Session) -> int:
    now = datetime.now(timezone.utc)
    stmt = (
        select(OrgEntitlement)
        .where(OrgEntitlement.trial_ends_at.is_not(None))
        .where(OrgEntitlement.trial_ends_at <= now)
        .where(OrgEntitlement.plan != PlanType.FREE)
    )
    expired = 0
    for entitlement in session.execute(stmt).scalars():
        if entitlement.stripe_status not in TRIAL_STATUSES:
            continue
        apply_plan(
            session=session,
            org_id=entitlement.org_id,
            plan=PlanType.FREE,
            trial_ends_at=None,
            stripe_subscription_id=None,
            stripe_price_id=None,
            stripe_status="expired",
        )
        expired += 1
    return expired


def allow_sync(snapshot: FeatureSnapshot, last_synced_at: datetime | None, now: datetime) -> bool:
    if last_synced_at is None:
        return True
    target = last_synced_at + timedelta(minutes=snapshot.sync_interval_minutes)
    return now >= target
