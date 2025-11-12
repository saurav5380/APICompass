from __future__ import annotations

from fastapi import APIRouter

from . import connections, health

router = APIRouter()
router.include_router(health.router)
router.include_router(connections.router)

__all__ = ["router", "connections", "health"]
