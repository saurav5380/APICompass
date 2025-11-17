from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta, timezone
from uuid import UUID, UUID as UUIDType

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from api_compass.core.config import settings
from api_compass.models.tables import AlertEvent, Budget, Connection, DailyUsageCost, RawUsageEvent
from api_compass.services import audit


def export_org_csv(session: Session, org_id: UUID) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["type", "id", "provider", "environment", "status", "metadata", "created_at"])

    for row in session.execute(select(Connection).where(Connection.org_id == org_id)).scalars():
        writer.writerow([
            "connection",
            row.id,
            row.provider.value,
            row.environment.value,
            row.status.value,
            (row.metadata_json or {}).get("masked_preview", "****"),
            row.created_at.isoformat(),
        ])

    for row in session.execute(select(Budget).where(Budget.org_id == org_id)).scalars():
        writer.writerow([
            "budget",
            row.id,
            row.provider.value if row.provider else "all",
            row.environment.value,
            "cap",
            f"{row.monthly_cap} {row.currency}",
            row.created_at.isoformat(),
        ])

    for row in session.execute(select(AlertEvent).where(AlertEvent.org_id == org_id)).scalars():
        env_label = row.environment.value if row.environment else ""
        writer.writerow([
            "alert_event",
            row.id,
            row.provider.value if row.provider else "all",
            env_label,
            row.severity.value,
            row.message,
            row.triggered_at.isoformat(),
        ])

    audit.log_action(
        session,
        org_id=org_id,
        action="org.exported",
        object_type="org",
        object_id=str(org_id),
        metadata={"format": "csv"},
    )
    return output.getvalue()


def purge_org_data(session: Session, org_id: UUID | str) -> None:
    if isinstance(org_id, str):
        org_id = UUIDType(org_id)
    session.execute(delete(AlertEvent).where(AlertEvent.org_id == org_id))
    session.execute(delete(DailyUsageCost).where(DailyUsageCost.org_id == org_id))
    session.execute(delete(RawUsageEvent).where(RawUsageEvent.org_id == org_id))
    session.execute(delete(Budget).where(Budget.org_id == org_id))
    session.execute(delete(Connection).where(Connection.org_id == org_id))
    audit.log_action(
        session,
        org_id=org_id,
        action="org.deleted",
        object_type="org",
        object_id=str(org_id),
        metadata={"scope": "purge"},
    )
    session.commit()


def purge_expired_events(session: Session) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.raw_event_retention_days)
    stmt = delete(RawUsageEvent).where(RawUsageEvent.ts < cutoff)
    result = session.execute(stmt)
    session.commit()
    return result.rowcount or 0
