from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api_compass.db.base import Base
from api_compass.models.enums import (
    AlertChannel,
    AlertFrequency,
    AlertSeverity,
    ConnectionStatus,
    EnvironmentType,
    PlanType,
    ProviderType,
    UserRole,
)
from api_compass.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


plan_enum = sa.Enum(PlanType, name="plan_type_enum")
user_role_enum = sa.Enum(UserRole, name="user_role_enum")
provider_enum = sa.Enum(ProviderType, name="provider_enum")
environment_enum = sa.Enum(EnvironmentType, name="environment_enum")
connection_status_enum = sa.Enum(ConnectionStatus, name="connection_status_enum")
alert_channel_enum = sa.Enum(AlertChannel, name="alert_channel_enum")
alert_frequency_enum = sa.Enum(AlertFrequency, name="alert_frequency_enum")
alert_severity_enum = sa.Enum(AlertSeverity, name="alert_severity_enum")


class Org(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "orgs"

    name: Mapped[str] = mapped_column(sa.String(length=255), nullable=False)
    plan: Mapped[PlanType] = mapped_column(
        plan_enum, nullable=False, server_default=PlanType.FREE.value
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(sa.String(length=255))

    users: Mapped[list["User"]] = relationship("User", back_populates="org", cascade="all, delete-orphan")
    connections: Mapped[list["Connection"]] = relationship(
        "Connection", back_populates="org", cascade="all, delete-orphan"
    )
    budgets: Mapped[list["Budget"]] = relationship("Budget", back_populates="org")
    alerts: Mapped[list["AlertRule"]] = relationship("AlertRule", back_populates="org")


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    org_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey("orgs.id"), nullable=False)
    email: Mapped[str] = mapped_column(sa.String(length=320), nullable=False)
    full_name: Mapped[str | None] = mapped_column(sa.String(length=255))
    role: Mapped[UserRole] = mapped_column(
        user_role_enum, nullable=False, server_default=UserRole.MEMBER.value
    )
    auth_provider: Mapped[str | None] = mapped_column(sa.String(length=50))
    external_id: Mapped[str | None] = mapped_column(sa.String(length=255))
    notification_preferences: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    org: Mapped[Org] = relationship("Org", back_populates="users")
    audit_logs: Mapped[list["AuditLogEntry"]] = relationship("AuditLogEntry", back_populates="user")

    __table_args__ = (
        sa.UniqueConstraint("org_id", "email", name="uq_users_org_email"),
    )


class Connection(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "connections"

    org_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey("orgs.id"), nullable=False)
    provider: Mapped[ProviderType] = mapped_column(provider_enum, nullable=False)
    environment: Mapped[EnvironmentType] = mapped_column(
        environment_enum, nullable=False, server_default=EnvironmentType.PROD.value
    )
    status: Mapped[ConnectionStatus] = mapped_column(
        connection_status_enum, nullable=False, server_default=ConnectionStatus.PENDING.value
    )
    display_name: Mapped[str | None] = mapped_column(sa.String(length=255))
    encrypted_auth_blob: Mapped[bytes] = mapped_column(sa.LargeBinary, nullable=False)
    scopes: Mapped[list[str] | None] = mapped_column(JSONB)
    metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    last_synced_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))

    org: Mapped[Org] = relationship("Org", back_populates="connections")
    raw_events: Mapped[list["RawUsageEvent"]] = relationship(
        "RawUsageEvent", back_populates="connection", cascade="all, delete-orphan"
    )

    __table_args__ = (
        sa.UniqueConstraint("org_id", "provider", "environment", name="uq_connections_scope"),
    )


class RawUsageEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "raw_usage_events"

    org_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey("orgs.id"), nullable=False)
    connection_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), sa.ForeignKey("connections.id", ondelete="SET NULL"), nullable=True
    )
    provider: Mapped[ProviderType] = mapped_column(provider_enum, nullable=False)
    environment: Mapped[EnvironmentType] = mapped_column(environment_enum, nullable=False)
    metric: Mapped[str] = mapped_column(sa.String(length=255), nullable=False)
    unit: Mapped[str] = mapped_column(sa.String(length=64), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(sa.Numeric(20, 6), nullable=False)
    unit_cost: Mapped[Decimal | None] = mapped_column(sa.Numeric(20, 6))
    cost: Mapped[Decimal | None] = mapped_column(sa.Numeric(20, 6))
    currency: Mapped[str] = mapped_column(sa.String(length=3), nullable=False, server_default="usd")
    ts: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    source: Mapped[str | None] = mapped_column(sa.String(length=50))
    metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    ingested_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False
    )

    org: Mapped[Org] = relationship("Org")
    connection: Mapped[Connection | None] = relationship("Connection", back_populates="raw_events")

    __table_args__ = (
        sa.Index("ix_raw_usage_events_org_ts", "org_id", "ts"),
        sa.Index("ix_raw_usage_events_provider_ts", "provider", "ts"),
    )


class DailyUsageCost(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "daily_usage_costs"

    org_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey("orgs.id"), nullable=False)
    provider: Mapped[ProviderType] = mapped_column(provider_enum, nullable=False)
    environment: Mapped[EnvironmentType] = mapped_column(environment_enum, nullable=False)
    day: Mapped[date] = mapped_column(sa.Date, nullable=False)
    quantity_sum: Mapped[Decimal] = mapped_column(sa.Numeric(20, 6), nullable=False)
    cost_sum: Mapped[Decimal] = mapped_column(sa.Numeric(20, 6), nullable=False)
    currency: Mapped[str] = mapped_column(sa.String(length=3), nullable=False, server_default="usd")
    confidence_min: Mapped[Decimal | None] = mapped_column(sa.Numeric(20, 6))
    confidence_max: Mapped[Decimal | None] = mapped_column(sa.Numeric(20, 6))

    org: Mapped[Org] = relationship("Org")

    __table_args__ = (
        sa.UniqueConstraint(
            "org_id", "provider", "environment", "day", name="uq_daily_usage_scope"
        ),
    )


class Budget(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "budgets"

    org_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey("orgs.id"), nullable=False)
    provider: Mapped[ProviderType | None] = mapped_column(provider_enum, nullable=True)
    environment: Mapped[EnvironmentType | None] = mapped_column(environment_enum, nullable=True)
    monthly_cap: Mapped[Decimal] = mapped_column(sa.Numeric(20, 2), nullable=False)
    currency: Mapped[str] = mapped_column(sa.String(length=3), nullable=False, server_default="usd")
    threshold_percent: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default="80")
    notes: Mapped[str | None] = mapped_column(sa.String(length=512))

    org: Mapped[Org] = relationship("Org", back_populates="budgets")
    alerts: Mapped[list["AlertRule"]] = relationship("AlertRule", back_populates="budget")


class AlertRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "alerts"

    org_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey("orgs.id"), nullable=False)
    budget_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), sa.ForeignKey("budgets.id", ondelete="SET NULL"), nullable=True
    )
    channel: Mapped[AlertChannel] = mapped_column(alert_channel_enum, nullable=False)
    frequency: Mapped[AlertFrequency] = mapped_column(alert_frequency_enum, nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(
        alert_severity_enum, nullable=False, server_default=AlertSeverity.WARNING.value
    )
    rule_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    quiet_hours_start: Mapped[time | None] = mapped_column(sa.Time(timezone=True))
    quiet_hours_end: Mapped[time | None] = mapped_column(sa.Time(timezone=True))
    debounce_minutes: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default="60")
    max_alerts_per_day: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default="10")
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.true())
    last_triggered_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))

    org: Mapped[Org] = relationship("Org", back_populates="alerts")
    budget: Mapped[Budget | None] = relationship("Budget", back_populates="alerts")


class AuditLogEntry(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "audit_log"

    org_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey("orgs.id"), nullable=False)
    user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(sa.String(length=128), nullable=False)
    object_type: Mapped[str] = mapped_column(sa.String(length=64), nullable=False)
    object_id: Mapped[str | None] = mapped_column(sa.String(length=64))
    metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    ip_address: Mapped[str | None] = mapped_column(sa.String(length=64))
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False
    )

    org: Mapped[Org] = relationship("Org")
    user: Mapped[User | None] = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        sa.Index("ix_audit_log_org_created", "org_id", "created_at"),
    )
