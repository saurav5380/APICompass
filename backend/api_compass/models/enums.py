from __future__ import annotations

from enum import StrEnum


class PlanType(StrEnum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class UserRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class ProviderType(StrEnum):
    OPENAI = "openai"
    TWILIO = "twilio"
    SENDGRID = "sendgrid"
    STRIPE = "stripe"
    GENERIC = "generic"


class EnvironmentType(StrEnum):
    PROD = "prod"
    STAGING = "staging"
    DEV = "dev"


class ConnectionStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    ERROR = "error"
    DISABLED = "disabled"


class AlertChannel(StrEnum):
    EMAIL = "email"
    SLACK = "slack"


class AlertFrequency(StrEnum):
    REALTIME = "real_time"
    HOURLY = "hourly"
    DAILY = "daily"


class AlertSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
