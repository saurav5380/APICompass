from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Final
from uuid import UUID

import redis

from api_compass.core.config import settings

logger = logging.getLogger(__name__)

_JOBS_SET: Final[str] = "connections:sync-jobs"
_CANCEL_PREFIX: Final[str] = "connections:cancel:"
_CLIENT = redis.Redis.from_url(str(settings.worker_broker_url), decode_responses=True)


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _connection_job_payload(connection_id: UUID) -> str:
    payload = {
        "connection_id": str(connection_id),
        "queued_at": _now_iso(),
    }
    return json.dumps(payload)


def schedule_sync(connection_id: UUID) -> None:
    try:
        timestamp = datetime.now(timezone.utc).timestamp()
        _CLIENT.zadd(_JOBS_SET, {_connection_job_payload(connection_id): timestamp})
    except redis.RedisError as exc:
        logger.warning("Unable to register sync job for connection %s: %s", connection_id, exc)


def cancel_scheduled_jobs(connection_id: UUID, ttl_seconds: int = 60) -> None:
    key = f"{_CANCEL_PREFIX}{connection_id}"
    try:
        _CLIENT.setex(key, ttl_seconds, _now_iso())
    except redis.RedisError as exc:
        logger.warning("Unable to cancel jobs for connection %s: %s", connection_id, exc)


def cancellation_key(connection_id: UUID) -> str:
    return f"{_CANCEL_PREFIX}{connection_id}"


def redis_client() -> redis.Redis:
    return _CLIENT
