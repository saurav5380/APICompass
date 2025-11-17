from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from api_compass.core.config import settings
from api_compass.core import telemetry

telemetry.setup_logging()
telemetry.setup_sentry()

celery_app = Celery(
    "api_compass",
    broker=str(settings.worker_broker_url),
    backend=str(settings.worker_result_backend),
    include=[
        "api_compass.workers.polling",
        "api_compass.workers.aggregates",
        "api_compass.workers.alerts",
        "api_compass.workers.entitlements",
        "api_compass.workers.cleanup",
    ],
)

celery_app.conf.update(
    timezone="UTC",
    enable_utc=True,
    task_default_queue="default",
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    worker_send_task_events=True,
)

celery_app.conf.beat_schedule = {
    "poll-openai-hourly": {
        "task": "api_compass.workers.polling.poll_openai",
        "schedule": crontab(minute=0),
        "options": {"queue": "polling"},
    },
    "poll-twilio-hourly": {
        "task": "api_compass.workers.polling.poll_twilio",
        "schedule": crontab(minute=0),
        "options": {"queue": "polling"},
    },
    "poll-sendgrid-hourly": {
        "task": "api_compass.workers.polling.poll_sendgrid",
        "schedule": crontab(minute=0),
        "options": {"queue": "polling"},
    },
    "alerts-evaluate": {
        "task": "alerts.evaluate",
        "schedule": crontab(minute="*/15"),
        "options": {"queue": "alerts"},
    },
    "alerts-daily-digest": {
        "task": "alerts.daily_digest",
        "schedule": crontab(minute=0, hour=settings.alerts_digest_hour_utc),
        "options": {"queue": "alerts"},
    },
    "entitlements-expire-trials": {
        "task": "entitlements.expire_trials",
        "schedule": crontab(minute="*/5"),
        "options": {"queue": "billing"},
    },
    "cleanup-expire-raw-events": {
        "task": "cleanup.expire_raw_events",
        "schedule": crontab(minute=30, hour=3),
        "options": {"queue": "cleanup"},
    },
}

__all__ = ("celery_app",)
