from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Iterator
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from api_compass.db.session import SessionLocal, apply_rls_scope, reset_rls_scope


API_KEY_PREFIX = "org_"


@dataclass(frozen=True)
class OrgScope:
    org_id: UUID
    token_source: str
    token_reference: str


def _org_id_from_api_key(api_key: str) -> UUID:
    if not api_key.startswith(API_KEY_PREFIX):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is not recognized for org scoping.",
        )

    parts = api_key.split("_", 2)
    if len(parts) < 2:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is not recognized for org scoping.",
        )

    try:
        return UUID(parts[1])
    except ValueError as exc:  # pragma: no cover - defensive
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is not recognized for org scoping.",
        ) from exc


def get_org_scope(
    x_org_id: Annotated[str | None, Header(alias="X-Org-Id")] = None,
    x_api_key: Annotated[str | None, Header(alias="X-Api-Key")] = None,
) -> OrgScope:
    if x_org_id and x_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either X-Org-Id or X-Api-Key, not both.",
        )

    if x_org_id:
        try:
            org_id = UUID(x_org_id)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="X-Org-Id must be a valid UUID.",
            ) from exc

        return OrgScope(org_id=org_id, token_source="header", token_reference="x-org-id")

    if x_api_key:
        org_id = _org_id_from_api_key(x_api_key)
        token_ref = f"api-key:*{x_api_key[-4:]}"
        return OrgScope(org_id=org_id, token_source="api_key", token_reference=token_ref)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Organization context missing. Supply X-Org-Id or X-Api-Key.",
    )


def get_db_session(org_scope: Annotated[OrgScope, Depends(get_org_scope)]) -> Iterator[Session]:
    session = SessionLocal()
    apply_rls_scope(session, org_scope.org_id)

    try:
        yield session
    finally:
        reset_rls_scope(session)
        session.close()
