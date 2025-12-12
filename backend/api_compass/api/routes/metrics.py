from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api_compass.api.deps import OrgScope, get_db_session, get_org_scope
from api_compass.models.enums import ProviderType
from api_compass.schemas.metrics import MetricsOverview, MetricsTrendPoint
from api_compass.services import metrics as metrics_service

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/overview", response_model=MetricsOverview)
def read_metrics_overview(
    start_date: date | None = None,
    end_date: date | None = None,
    provider: ProviderType | None = None,
    session: Session = Depends(get_db_session),
    org_scope: OrgScope = Depends(get_org_scope),
) -> MetricsOverview:
    return metrics_service.get_overview(
        session=session,
        org_id=org_scope.org_id,
        start_date=start_date,
        end_date=end_date,
        provider=provider,
    )


@router.get("/trends", response_model=list[MetricsTrendPoint])
def read_metrics_trends(
    start_date: date | None = None,
    end_date: date | None = None,
    provider: ProviderType | None = None,
    session: Session = Depends(get_db_session),
    org_scope: OrgScope = Depends(get_org_scope),
) -> list[MetricsTrendPoint]:
    return metrics_service.get_trends(
        session=session,
        org_id=org_scope.org_id,
        start_date=start_date,
        end_date=end_date,
        provider=provider,
    )
