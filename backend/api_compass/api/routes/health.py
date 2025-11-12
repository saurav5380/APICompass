from __future__ import annotations

from contextlib import closing

import redis
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api_compass.core.config import settings
from api_compass.db.session import SessionLocal

router = APIRouter(tags=["health"])


def _check_database() -> dict[str, str]:
    try:
        with closing(SessionLocal()) as session:
            session.execute(text("SELECT 1"))
        return {"status": "ok"}
    except SQLAlchemyError as exc:
        return {"status": "error", "detail": str(exc)}


def _check_worker() -> dict[str, str]:
    try:
        client = redis.Redis.from_url(
            str(settings.worker_broker_url),
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        client.ping()
        return {"status": "ok"}
    except redis.RedisError as exc:
        return {"status": "error", "detail": str(exc)}


@router.get("/health", summary="Liveness probe")
def read_health() -> dict[str, str]:
    return {"status": "ok", "service": settings.project_name}


@router.get("/healthz", summary="Readiness probe")
def read_healthz() -> JSONResponse:
    db = _check_database()
    worker = _check_worker()
    components = {"database": db, "worker": worker}
    overall_ok = all(component.get("status") == "ok" for component in components.values())
    status_code = status.HTTP_200_OK if overall_ok else status.HTTP_503_SERVICE_UNAVAILABLE

    payload = {
        "service": settings.project_name,
        "version": settings.version,
        "status": "ok" if overall_ok else "error",
        "components": components,
    }

    return JSONResponse(status_code=status_code, content=payload)
