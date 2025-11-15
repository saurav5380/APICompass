from __future__ import annotations

from celery.utils.log import get_task_logger

from api_compass.celery_app import celery_app
from api_compass.db.session import SessionLocal
from api_compass.services import entitlements as entitlement_service

logger = get_task_logger(__name__)


@celery_app.task(name="entitlements.expire_trials")
def expire_trials_task() -> int:  # type: ignore[override]
    with SessionLocal() as session:
        expired = entitlement_service.expire_trials(session)
    if expired:
        logger.info("Downgraded %s orgs after trial expiration", expired)
    return expired
