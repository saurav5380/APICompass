from __future__ import annotations

import argparse
from typing import Any

import stripe

from api_compass.core.config import get_settings
from api_compass.core.plans import PLAN_DEFINITIONS, PlanDefinition


def _find_product(plan: PlanDefinition) -> Any | None:
    products = stripe.Product.list(limit=100)
    for product in products.auto_paging_iter():
        metadata = getattr(product, "metadata", {}) or {}
        if metadata.get("plan_type") == plan.plan.value:
            return product
    return None


def _ensure_product(plan: PlanDefinition) -> Any:
    product = _find_product(plan)
    if product:
        return product
    return stripe.Product.create(
        name=f"API Compass {plan.label}",
        description=plan.description,
        metadata={"plan_type": plan.plan.value},
    )


def _ensure_price(plan: PlanDefinition, product: Any, currency: str) -> Any:
    assert plan.stripe_lookup_key, "Lookup key required"
    assert plan.unit_amount_cents, "Unit amount required"
    prices = stripe.Price.list(lookup_keys=[plan.stripe_lookup_key], limit=1)
    if prices.data:
        price = prices.data[0]
        if not price.active:
            stripe.Price.modify(price.id, active=True)
        return price

    return stripe.Price.create(
        nickname=f"{plan.label} monthly",
        lookup_key=plan.stripe_lookup_key,
        unit_amount=plan.unit_amount_cents,
        currency=currency,
        recurring={"interval": "month"},
        product=product.id,
        metadata={"plan_type": plan.plan.value},
        trial_period_days=plan.trial_days,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap Stripe plans/prices for API Compass")
    parser.add_argument("--currency", default="usd", help="ISO currency code for paid plans")
    args = parser.parse_args()

    settings = get_settings()
    stripe.api_key = settings.stripe_secret_key.get_secret_value()

    for plan in PLAN_DEFINITIONS.values():
        if not plan.stripe_lookup_key or not plan.unit_amount_cents:
            continue
        product = _ensure_product(plan)
        price = _ensure_price(plan, product, args.currency)
        print(
            f"{plan.plan.value}: product={product.id} price={price.id} lookup={plan.stripe_lookup_key} trial_days={plan.trial_days}"
        )


if __name__ == "__main__":
    main()
