from __future__ import annotations

import logging
import time
from typing import Any

import sentry_sdk
from fastapi import Request
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

from api_compass.core.config import settings

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(level=level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def setup_sentry() -> None:
    dsn = settings.sentry_dsn.get_secret_value() if settings.sentry_dsn else None
    if not dsn:
        return

    sentry_sdk.init(
        dsn=dsn,
        environment=settings.environment,
        traces_sample_rate=0.01,
        enable_tracing=True,
        integrations=[FastApiIntegration(transaction_style="endpoint"), CeleryIntegration()],
    )


def bind_request_context(request: Request) -> None:
    if not sentry_sdk.Hub.current.client:
        return
    with sentry_sdk.configure_scope() as scope:
        org_id = request.headers.get("X-Org-Id") or request.headers.get("X-Api-Key")
        if org_id:
            scope.set_tag("org", org_id)
        scope.set_tag("path", request.url.path)
        scope.set_tag("method", request.method)


def capture_exception(err: BaseException, context: dict[str, Any] | None = None) -> None:
    if context:
        with sentry_sdk.push_scope() as scope:
            for key, value in context.items():
                scope.set_extra(key, value)
            sentry_sdk.capture_exception(err)
    else:
        sentry_sdk.capture_exception(err)


def log_request(request: Request, status_code: int, duration_ms: float) -> None:
    logger.info(
        "HTTP %s %s -> %s in %.1fms",
        request.method,
        request.url.path,
        status_code,
        duration_ms,
    )
