from __future__ import annotations

from celery.utils.log import get_task_logger

from api_compass.celery_app import celery_app
from api_compass.services import alerts as alert_service

logger = get_task_logger(__name__)


@celery_app.task(name="alerts.evaluate")
def evaluate_alerts_task() -> None:
    logger.info("Starting alert evaluation sweep")
    alert_service.evaluate_all_orgs()
    logger.info("Alert evaluation sweep finished")


@celery_app.task(name="alerts.daily_digest")
def send_daily_digest_task() -> None:
    logger.info("Sending daily usage digests")
    alert_service.send_daily_digests()
    logger.info("Daily usage digests complete")
