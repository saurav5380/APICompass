from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from api_compass.models.enums import PlanType


class TrialInfo(BaseModel):
    active: bool
    ends_at: datetime | None


class FeatureFlags(BaseModel):
    plan: PlanType
    max_providers: int
    sync_interval_minutes: int
    digest_frequency: str
    alerts_enabled: bool
    tips_enabled: bool
    stripe_status: str
    trial: TrialInfo

    model_config = {"from_attributes": True}


__all__ = ["FeatureFlags", "TrialInfo"]
