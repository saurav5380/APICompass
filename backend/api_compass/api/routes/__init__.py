from __future__ import annotations

from fastapi import APIRouter

from . import billing, budgets, connections, data, health, ingest, usage

router = APIRouter()
router.include_router(health.router)
router.include_router(connections.router)
router.include_router(usage.router)
router.include_router(budgets.router)
router.include_router(billing.router)
router.include_router(data.router)
router.include_router(ingest.router)

__all__ = ["router", "billing", "budgets", "connections", "data", "health", "usage", "ingest"]
