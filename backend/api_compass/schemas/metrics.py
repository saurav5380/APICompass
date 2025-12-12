from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from api_compass.models.enums import ProviderType


class MetricsOverview(BaseModel):
  start_date: date
  end_date: date
  provider: ProviderType | None = None
  total_calls: int
  total_errors: int
  total_spend: Decimal


class MetricsTrendPoint(BaseModel):
  day: date
  calls: int
  errors: int
  spend: Decimal
