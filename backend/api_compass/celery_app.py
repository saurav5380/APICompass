from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from api_compass.core.config import settings

celery_app = Celery(
    "api_compass",
    broker=str(settings.worker_broker_url),
    backend=str(settings.worker_result_backend),
    include=["api_compass.workers.polling"],
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
}

__all__ = ("celery_app",)
