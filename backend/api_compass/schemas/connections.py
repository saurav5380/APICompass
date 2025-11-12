from __future__ import annotations

from datetime import datetime
from typing import List
from uuid import UUID

from pydantic import BaseModel, Field, SecretStr

from api_compass.models.enums import ConnectionStatus, EnvironmentType, ProviderType


class ConnectionCreate(BaseModel):
    provider: ProviderType
    environment: EnvironmentType = EnvironmentType.PROD
    display_name: str | None = Field(default=None, max_length=255)
    api_key: SecretStr = Field(description="Provider API key or token.")
    scopes: List[str] = Field(default_factory=list, description="Minimal scopes requested for the integration.")


class ConnectionRead(BaseModel):
    id: UUID
    provider: ProviderType
    environment: EnvironmentType
    display_name: str | None
    status: ConnectionStatus
    scopes: list[str]
    masked_key: str
    created_at: datetime
    last_synced_at: datetime | None

    model_config = {"from_attributes": True}
