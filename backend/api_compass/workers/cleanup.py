from __future__ import annotations

from celery.utils.log import get_task_logger

from api_compass.celery_app import celery_app
from api_compass.db.session import SessionLocal
from api_compass.services import data_ops

logger = get_task_logger(__name__)


@celery_app.task(name="cleanup.expire_raw_events")
def expire_raw_events_task() -> int:  # type: ignore[override]
    with SessionLocal() as session:
        removed = data_ops.purge_expired_events(session)
    if removed:
        logger.info("Expired %s raw events per retention policy", removed)
    return removed


@celery_app.task(name="cleanup.delete_org_data")
def delete_org_data_task(org_id: str) -> str:  # type: ignore[override]
    with SessionLocal() as session:
        data_ops.purge_org_data(session, org_id)
    logger.info("Purged org data for %s", org_id)
    return org_id
