from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.orm import Session

from api_compass.api.deps import OrgScope, get_db_session, get_org_scope
from api_compass.schemas import ConnectionCreate, ConnectionRead
from api_compass.services import connections as connection_service
from api_compass.services.entitlements import PlanLimitError

router = APIRouter(prefix="/connections", tags=["connections"])


@router.post("/", response_model=ConnectionRead, status_code=status.HTTP_201_CREATED)
def create_connection(
    payload: ConnectionCreate,
    session: Session = Depends(get_db_session),
    org_scope: OrgScope = Depends(get_org_scope),
) -> ConnectionRead:
    try:
        return connection_service.create_connection(session, org_scope.org_id, payload)
    except IntegrityError as exc:
        detail = "Connection already exists for this provider/environment."
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from exc
    except PlanLimitError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("/", response_model=list[ConnectionRead])
def list_connections(
    session: Session = Depends(get_db_session),
    org_scope: OrgScope = Depends(get_org_scope),
) -> list[ConnectionRead]:
    return connection_service.list_connections(session, org_scope.org_id)


@router.delete("/{connection_id}", response_model=ConnectionRead)
def revoke_connection(
    connection_id: UUID,
    session: Session = Depends(get_db_session),
    org_scope: OrgScope = Depends(get_org_scope),
) -> ConnectionRead:
    try:
        return connection_service.revoke_connection(session, org_scope.org_id, connection_id)
    except NoResultFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found.") from exc
