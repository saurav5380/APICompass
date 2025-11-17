from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from api_compass.api.deps import OrgScope, get_db_session, get_org_scope
from api_compass.services import data_ops
from api_compass.celery_app import celery_app

router = APIRouter(prefix="/data", tags=["data"])


@router.get("/export", response_class=Response)
def export_org_data(
    session: Session = Depends(get_db_session),
    org_scope: OrgScope = Depends(get_org_scope),
) -> Response:
    csv_blob = data_ops.export_org_csv(session, org_scope.org_id)
    return Response(
        content=csv_blob,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=org-{org_scope.org_id}.csv"},
    )


@router.post("/delete", status_code=status.HTTP_202_ACCEPTED)
def delete_org_data(org_scope: OrgScope = Depends(get_org_scope)) -> dict[str, str]:
    try:
        celery_app.send_task(
            "cleanup.delete_org_data",
            args=[str(org_scope.org_id)],
            queue="cleanup",
        )
    except Exception as exc:  # pragma: no cover - enqueue failure
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    return {"status": "scheduled", "org_id": str(org_scope.org_id)}
