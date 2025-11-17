from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from api_compass.models.tables import AuditLogEntry


def log_action(
    session: Session,
    *,
    org_id: UUID,
    action: str,
    object_type: str,
    object_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    user_id: UUID | None = None,
    ip_address: str | None = None,
) -> AuditLogEntry:
    entry = AuditLogEntry(
        org_id=org_id,
        user_id=user_id,
        action=action,
        object_type=object_type,
        object_id=object_id,
        metadata_json=metadata,
        ip_address=ip_address,
        created_at=datetime.now(timezone.utc),
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry
