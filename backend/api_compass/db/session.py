from __future__ import annotations

from typing import Iterator
from uuid import UUID

from sqlalchemy import bindparam, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from api_compass.core.config import settings

DATABASE_URL = str(settings.database_url)

engine = create_engine(DATABASE_URL, echo=False, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

_SET_ORG_SCOPE = text(
    "SELECT set_config('app.current_org_id', (:org_id)::text, false)"
).bindparams(bindparam("org_id"))
_SET_RLS_ROLE = text("SET ROLE apicompass_rls")
_RESET_RLS_ROLE = text("RESET ROLE")
_RESET_ORG_SCOPE = text("RESET app.current_org_id")


def apply_rls_scope(session: Session, org_id: UUID) -> None:
    """Set the per-session PostgreSQL GUC used by RLS policies."""
    session.execute(_SET_RLS_ROLE)
    session.execute(_SET_ORG_SCOPE, {"org_id": str(org_id)})


def reset_rls_scope(session: Session) -> None:
    session.execute(_RESET_ORG_SCOPE)
    session.execute(_RESET_RLS_ROLE)


def get_session(org_id: UUID | None = None) -> Iterator[Session]:
    session = SessionLocal()
    role_applied = False
    try:
        if org_id is not None:
            apply_rls_scope(session, org_id)
            role_applied = True
        yield session
    finally:
        if role_applied:
            reset_rls_scope(session)
        session.close()
