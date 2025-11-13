from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field

from api_compass.models.enums import EnvironmentType, ProviderType


class UsageProjection(BaseModel):
    provider: ProviderType
    environment: EnvironmentType
    currency: str = Field(default="usd")
    month_to_date_spend: Decimal
    projected_total: Decimal
    projected_min: Decimal
    projected_max: Decimal
    rolling_avg_7d: Decimal | None = None
    rolling_avg_14d: Decimal | None = None
    sample_days: int
    tooltip: str

    model_config = {"from_attributes": True}
