from __future__ import annotations

from fastapi import APIRouter

from . import billing, budgets, connections, health, usage

router = APIRouter()
router.include_router(health.router)
router.include_router(connections.router)
router.include_router(usage.router)
router.include_router(budgets.router)
router.include_router(billing.router)

__all__ = ["router", "billing", "budgets", "connections", "health", "usage"]
