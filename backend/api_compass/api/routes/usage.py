from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api_compass.api.deps import OrgScope, get_db_session, get_org_scope
from api_compass.models.enums import EnvironmentType, ProviderType
from api_compass.schemas import UsageProjection, UsageTip
from api_compass.services import entitlements as entitlement_service
from api_compass.services import tips as tips_service
from api_compass.services import usage as usage_service

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("/projections", response_model=list[UsageProjection])
def read_usage_projections(
    environment: EnvironmentType = EnvironmentType.PROD,
    provider: ProviderType | None = None,
    session: Session = Depends(get_db_session),
    org_scope: OrgScope = Depends(get_org_scope),
) -> list[UsageProjection]:
    projections = usage_service.get_usage_projections(
        session=session,
        org_id=org_scope.org_id,
        environment=environment,
        provider=provider,
    )

    if provider and not projections:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No usage data found for the requested provider.",
        )

    return [
        UsageProjection(
            provider=projection.provider,
            environment=projection.environment,
            currency=projection.currency,
            month_to_date_spend=projection.month_to_date,
            projected_total=projection.projected_total,
            projected_min=projection.projected_min,
            projected_max=projection.projected_max,
            rolling_avg_7d=projection.rolling_avg_7d,
            rolling_avg_14d=projection.rolling_avg_14d,
            sample_days=projection.sample_days,
            tooltip=projection.tooltip,
            budget_limit=projection.budget_limit,
            budget_remaining=projection.budget_remaining,
            budget_gap=projection.budget_gap,
            budget_consumed_percent=projection.budget_consumed_percent,
            budget_source=projection.budget_source,
            over_budget=projection.over_budget,
        )
        for projection in projections
    ]


@router.get("/tips", response_model=list[UsageTip])
def read_usage_tips(
    environment: EnvironmentType = EnvironmentType.PROD,
    session: Session = Depends(get_db_session),
    org_scope: OrgScope = Depends(get_org_scope),
) -> list[UsageTip]:
    entitlements = entitlement_service.get_entitlements(session, org_scope.org_id)
    if not entitlements.tips_enabled:
        return []
    tips = tips_service.get_usage_tips(
        session=session,
        org_id=org_scope.org_id,
        environment=environment,
    )
    return tips
