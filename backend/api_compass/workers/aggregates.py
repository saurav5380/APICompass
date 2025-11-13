from __future__ import annotations

from typing import Any

from celery.utils.log import get_task_logger

from api_compass.celery_app import celery_app
from api_compass.core.config import settings
from api_compass.services import usage as usage_service

logger = get_task_logger(__name__)


@celery_app.task(name="usage.refresh_daily_usage_costs")
def refresh_daily_usage_costs(days: int | None = None) -> dict[str, Any]:
    target_days = days or settings.usage_backfill_days
    logger.info("Starting daily usage backfill for last %s days", target_days)

    try:
        result = usage_service.refresh_daily_usage_costs(
            target_days,
            max_seconds=settings.usage_backfill_timeout_seconds,
        )
    except TimeoutError as exc:
        logger.warning("Daily usage backfill aborted: %s", exc)
        raise

    logger.info(
        "Completed daily usage backfill windows=%s duration=%.2fs",
        result["windows"],
        result["duration_seconds"],
    )
    return result
