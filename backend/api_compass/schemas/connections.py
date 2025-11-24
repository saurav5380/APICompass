from __future__ import annotations

from datetime import datetime
from typing import List
from uuid import UUID

from pydantic import BaseModel, Field, SecretStr, model_validator

from api_compass.models.enums import ConnectionStatus, EnvironmentType, ProviderType


class ConnectionCreate(BaseModel):
    provider: ProviderType
    environment: EnvironmentType = EnvironmentType.PROD
    display_name: str | None = Field(default=None, max_length=255)
    api_key: SecretStr | None = Field(default=None, description="Provider API key or token.")
    scopes: List[str] = Field(default_factory=list, description="Minimal scopes requested for the integration.")
    local_connector_enabled: bool = Field(
        default=False,
        description="Enable Local Connector mode to keep provider secrets on-device.",
    )

    @model_validator(mode="after")
    def enforce_auth_mode(self) -> "ConnectionCreate":
        if not self.local_connector_enabled and self.api_key is None:
            raise ValueError("api_key is required when Local Connector mode is disabled.")
        return self


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
    local_connector_enabled: bool
    local_agent_last_seen_at: datetime | None
    local_agent_token: str | None = Field(
        default=None,
        description="Newly issued Local Connector agent token; returned only at creation time.",
    )

    model_config = {"from_attributes": True}
