from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from api_compass.models.enums import EnvironmentType, ProviderType


class BudgetBase(BaseModel):
    provider: ProviderType | None = Field(
        default=None,
        description="Optional provider-specific budget. Null applies to all providers.",
    )
    environment: EnvironmentType = Field(default=EnvironmentType.PROD)
    monthly_cap: Decimal = Field(gt=0, decimal_places=2)
    currency: str = Field(default="USD", description="Three-letter ISO currency code.")

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        normalized = value.upper()
        if len(normalized) != 3 or not normalized.isalpha():
            msg = "Currency must be a three-letter ISO code."
            raise ValueError(msg)
        return normalized


class BudgetCreate(BudgetBase):
    pass


class BudgetRead(BudgetBase):
    id: str

    model_config = {"from_attributes": True}
