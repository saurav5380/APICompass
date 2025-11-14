from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session

from api_compass.models.enums import EnvironmentType, ProviderType
from api_compass.models.tables import Budget
from api_compass.schemas import BudgetCreate, BudgetRead


def _normalize_environment(environment: EnvironmentType | None) -> EnvironmentType:
    return environment or EnvironmentType.PROD


def _fetch_existing(
    session: Session,
    org_id: UUID,
    provider: ProviderType | None,
    environment: EnvironmentType,
) -> Budget | None:
    stmt = (
        select(Budget)
        .where(Budget.org_id == org_id)
        .where(Budget.provider == provider)
        .where(Budget.environment == environment)
    )
    return session.execute(stmt).scalar_one_or_none()


def list_budgets(session: Session, org_id: UUID) -> list[BudgetRead]:
    stmt = (
        select(Budget)
        .where(Budget.org_id == org_id)
        .order_by(Budget.provider, Budget.environment)
    )
    budgets = session.execute(stmt).scalars().all()
    return [
        BudgetRead(
            id=str(budget.id),
            provider=budget.provider,
            environment=budget.environment or EnvironmentType.PROD,
            monthly_cap=Decimal(budget.monthly_cap),
            currency=budget.currency.upper(),
        )
        for budget in budgets
    ]


def upsert_budget(session: Session, org_id: UUID, payload: BudgetCreate) -> BudgetRead:
    environment = _normalize_environment(payload.environment)
    provider = payload.provider

    existing = _fetch_existing(session, org_id, provider, environment)
    if existing:
        existing.monthly_cap = payload.monthly_cap
        existing.currency = payload.currency
        session.add(existing)
        session.commit()
        session.refresh(existing)
        target = existing
    else:
        budget = Budget(
            org_id=org_id,
            provider=provider,
            environment=environment,
            monthly_cap=payload.monthly_cap,
            currency=payload.currency,
        )
        session.add(budget)
        session.commit()
        session.refresh(budget)
        target = budget

    return BudgetRead(
        id=str(target.id),
        provider=target.provider,
        environment=target.environment or EnvironmentType.PROD,
        monthly_cap=Decimal(target.monthly_cap),
        currency=target.currency.upper(),
    )


def delete_budget(session: Session, org_id: UUID, budget_id: UUID) -> None:
    stmt = select(Budget).where(Budget.id == budget_id).where(Budget.org_id == org_id)
    budget = session.execute(stmt).scalar_one_or_none()
    if budget is None:
        raise NoResultFound
    session.delete(budget)
    session.commit()
