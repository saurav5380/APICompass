from __future__ import annotations

import random
import time
from datetime import datetime, timezone
from uuid import UUID

import redis
from celery import Task
from celery.utils.log import get_task_logger
from sqlalchemy import select
from sqlalchemy.orm import Session

from api_compass.celery_app import celery_app
from api_compass.core.config import settings
from api_compass.db.session import SessionLocal
from api_compass.models.enums import ConnectionStatus, ProviderType
from api_compass.models.tables import Connection
from api_compass.core import telemetry
from api_compass.services import entitlements as entitlement_service
from api_compass.services import usage as usage_service
from api_compass.services.jobs import redis_client

logger = get_task_logger(__name__)


class ProviderAPIError(Exception):
    """Base exception for provider polling failures."""

    def __init__(self, provider: ProviderType, connection_id: UUID, status_code: int, message: str | None = None):
        self.provider = provider
        self.connection_id = connection_id
        self.status_code = status_code
        self.message = message or "Provider API error"
        super().__init__(f"{provider.value} poll failed for {connection_id}: {self.message} ({status_code})")


class RetryableProviderError(ProviderAPIError):
    """Raised when providers respond with 429 or transient 5xx errors."""


class ProviderPollTask(Task):
    """Base task that configures automatic retries/backoff for transient provider failures."""

    abstract = True
    autoretry_for = (RetryableProviderError,)
    retry_backoff = settings.worker_retry_backoff_seconds
    retry_backoff_max = settings.worker_retry_backoff_seconds * 8
    retry_jitter = True
    max_retries = settings.worker_retry_max_attempts


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _polling_bucket() -> str:
    interval = max(settings.worker_poll_interval_seconds, 60)
    current_epoch = int(_now().timestamp())
    bucket = current_epoch // interval
    return str(bucket)


def _idempotency_key(provider: ProviderType, connection_id: UUID, bucket: str) -> str:
    return f"connections:poll:{provider.value}:{connection_id}:{bucket}"


def _acquire_idempotency_lock(
    client: redis.Redis,
    provider: ProviderType,
    connection_id: UUID,
    bucket: str,
) -> bool:
    key = _idempotency_key(provider, connection_id, bucket)
    ttl = settings.worker_idempotency_ttl_seconds
    try:
        acquired = client.set(key, _now().isoformat(), nx=True, ex=ttl)
        if not acquired:
            logger.debug(
                "Skipping poll for %s connection %s; already processed within window %s",
                provider.value,
                connection_id,
                bucket,
            )
        return bool(acquired)
    except redis.RedisError as exc:  # pragma: no cover - defensive guard that keeps job moving
        logger.warning("Unable to enforce idempotency for %s: %s", key, exc)
        return True


def _active_connections(session: Session, provider: ProviderType) -> list[Connection]:
    stmt = (
        select(Connection)
        .where(Connection.provider == provider, Connection.status == ConnectionStatus.ACTIVE)
        .where(Connection.local_connector_enabled.is_(False))
        .order_by(Connection.created_at.asc())
    )
    return session.execute(stmt).scalars().all()


def _maybe_raise_simulated_error(connection: Connection) -> None:
    metadata = connection.metadata_json or {}
    status_override = metadata.get("simulate_status")
    if status_override is None:
        return

    try:
        status_code = int(status_override)
    except (TypeError, ValueError) as exc:
        raise ProviderAPIError(connection.provider, connection.id, 400, "invalid simulate_status") from exc

    if status_code == 429 or status_code >= 500:
        raise RetryableProviderError(connection.provider, connection.id, status_code, "transient provider error")
    if status_code >= 400:
        raise ProviderAPIError(connection.provider, connection.id, status_code, "provider rejected request")


def _apply_jitter_delay(batch_size: int) -> None:
    """Distribute work within ±10% of the interval without blocking the entire worker."""

    if batch_size <= 1:
        return

    interval = max(settings.worker_poll_interval_seconds, 60)
    total_window = interval * settings.worker_poll_jitter_ratio
    if total_window <= 0:
        return

    per_connection_window = total_window / batch_size
    if per_connection_window <= 0:
        return

    offset = random.uniform(0, per_connection_window)
    if offset > 0:
        time.sleep(offset)


def _poll_provider(provider: ProviderType) -> int:
    bucket = _polling_bucket()
    processed = 0
    start = time.monotonic()
    redis_conn = redis_client()
    entitlements_cache: dict[UUID, entitlement_service.FeatureSnapshot] = {}

    with SessionLocal() as session:
        connections = _active_connections(session, provider)
        if not connections:
            logger.info("No %s connections found for hourly poll.", provider.value)
            return 0

        logger.info("Polling %s connections for provider %s", len(connections), provider.value)
        random.shuffle(connections)
        for connection in connections:
            if not _acquire_idempotency_lock(redis_conn, provider, connection.id, bucket):
                continue
            snapshot = entitlements_cache.get(connection.org_id)
            if snapshot is None:
                snapshot = entitlement_service.get_entitlements(session, connection.org_id)
                entitlements_cache[connection.org_id] = snapshot
            ts = _now()
            if not entitlement_service.allow_sync(snapshot, connection.last_synced_at, ts):
                continue

            _apply_jitter_delay(len(connections))
            try:
                _maybe_raise_simulated_error(connection)
                samples = usage_service.build_provider_samples(connection, ts)
                if not samples:
                    logger.info("Connection %s has no usage samples for provider %s", connection.id, provider.value)
                    continue

                created = usage_service.save_usage_samples(session, samples)
                if created == 0:
                    logger.info("Usage already ingested for %s connection %s at %s", provider.value, connection.id, ts.date())
                    continue

                session.flush()
                mtd_spend = usage_service.month_to_date_spend(
                    session, connection.org_id, connection.provider, connection.environment
                )
                summary = usage_service.describe_samples(samples)

                connection.last_synced_at = ts
                session.add(connection)
                try:
                    session.commit()
                except Exception:
                    session.rollback()
                    raise

                processed += 1
                logger.info(
                    "Polled %s connection=%s org=%s metrics=%s daily_cost=%s mtd_cost=%s",
                    provider.value,
                    connection.id,
                    connection.org_id,
                    summary["metrics"],
                    summary["total_cost"],
                    mtd_spend,
                )
            except Exception as exc:
                telemetry.capture_exception(
                    exc,
                    {
                        "org_id": str(connection.org_id),
                        "connection_id": str(connection.id),
                        "provider": connection.provider.value,
                        "environment": connection.environment.value,
                    },
                )
                logger.exception("Polling failed for connection %s org %s", connection.id, connection.org_id)

    duration = time.monotonic() - start
    logger.info("Finished %s poll with %s successful syncs in %.2fs", provider.value, processed, duration)
    return processed


@celery_app.task(name="poll_openai", bind=True, base=ProviderPollTask)
def poll_openai(self) -> int:  # type: ignore[override]
    return _poll_provider(ProviderType.OPENAI)


@celery_app.task(name="poll_twilio", bind=True, base=ProviderPollTask)
def poll_twilio(self) -> int:  # type: ignore[override]
    return _poll_provider(ProviderType.TWILIO)


@celery_app.task(name="poll_sendgrid", bind=True, base=ProviderPollTask)
def poll_sendgrid(self) -> int:  # type: ignore[override]
    return _poll_provider(ProviderType.SENDGRID)


__all__ = ("poll_openai", "poll_twilio", "poll_sendgrid", "ProviderAPIError", "RetryableProviderError")
