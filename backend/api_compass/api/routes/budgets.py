from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session

from api_compass.api.deps import OrgScope, get_db_session, get_org_scope
from api_compass.schemas import BudgetCreate, BudgetRead
from api_compass.services import budgets as budget_service

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.get("/", response_model=list[BudgetRead])
def list_budgets(
    session: Session = Depends(get_db_session),
    org_scope: OrgScope = Depends(get_org_scope),
) -> list[BudgetRead]:
    return budget_service.list_budgets(session, org_scope.org_id)


@router.post("/", response_model=BudgetRead, status_code=status.HTTP_201_CREATED)
def create_or_update_budget(
    payload: BudgetCreate,
    session: Session = Depends(get_db_session),
    org_scope: OrgScope = Depends(get_org_scope),
) -> BudgetRead:
    return budget_service.upsert_budget(session, org_scope.org_id, payload)


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(
    budget_id: UUID,
    session: Session = Depends(get_db_session),
    org_scope: OrgScope = Depends(get_org_scope),
) -> None:
    try:
        budget_service.delete_budget(session, org_scope.org_id, budget_id)
    except NoResultFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found.") from exc
