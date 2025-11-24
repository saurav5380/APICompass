from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from api_compass.models.enums import EnvironmentType, ProviderType


class LocalUsageSample(BaseModel):
    metric: str = Field(min_length=1, max_length=255)
    unit: str = Field(min_length=1, max_length=64)
    quantity: Decimal
    unit_cost: Decimal | None = None
    currency: str = Field(default="usd", min_length=3, max_length=3)
    ts: datetime
    metadata: dict[str, Any] | None = None


class LocalUsageIngest(BaseModel):
    connection_id: UUID
    provider: ProviderType
    environment: EnvironmentType
    source: str = Field(default="local-agent", min_length=3, max_length=50)
    agent_version: str = Field(default="local-connector/1.0", min_length=3, max_length=64)
    samples: list[LocalUsageSample] = Field(min_length=1)
