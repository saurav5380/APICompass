"""initial schema with timescale hypertable"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


plan_type_enum = postgresql.ENUM("free", "pro", "enterprise", name="plan_type_enum")
user_role_enum = postgresql.ENUM(
    "owner", "admin", "member", "viewer", name="user_role_enum"
)
provider_enum = postgresql.ENUM(
    "openai", "twilio", "sendgrid", "stripe", "generic", name="provider_enum"
)
environment_enum = postgresql.ENUM("prod", "staging", "dev", name="environment_enum")
connection_status_enum = postgresql.ENUM(
    "pending", "active", "error", "disabled", name="connection_status_enum"
)
alert_channel_enum = postgresql.ENUM("email", "slack", name="alert_channel_enum")
alert_frequency_enum = postgresql.ENUM(
    "real_time", "hourly", "daily", name="alert_frequency_enum"
)
alert_severity_enum = postgresql.ENUM(
    "info", "warning", "critical", name="alert_severity_enum"
)


def upgrade() -> None:
    bind = op.get_bind()

    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb;")

    plan_type_enum.create(bind, checkfirst=True)
    user_role_enum.create(bind, checkfirst=True)
    provider_enum.create(bind, checkfirst=True)
    environment_enum.create(bind, checkfirst=True)
    connection_status_enum.create(bind, checkfirst=True)
    alert_channel_enum.create(bind, checkfirst=True)
    alert_frequency_enum.create(bind, checkfirst=True)
    alert_severity_enum.create(bind, checkfirst=True)

    op.create_table(
        "orgs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("plan", plan_type_enum, nullable=False, server_default="free"),
        sa.Column("stripe_customer_id", sa.String(length=255)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=255)),
        sa.Column("role", user_role_enum, nullable=False, server_default="member"),
        sa.Column("auth_provider", sa.String(length=50)),
        sa.Column("external_id", sa.String(length=255)),
        sa.Column("notification_preferences", postgresql.JSONB),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.UniqueConstraint("org_id", "email", name="uq_users_org_email"),
    )

    op.create_table(
        "budgets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("provider", provider_enum),
        sa.Column("environment", environment_enum),
        sa.Column("monthly_cap", sa.Numeric(20, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="usd"),
        sa.Column("threshold_percent", sa.Integer, nullable=False, server_default="80"),
        sa.Column("notes", sa.String(length=512)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
    )

    op.create_table(
        "connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("provider", provider_enum, nullable=False),
        sa.Column("environment", environment_enum, nullable=False, server_default="prod"),
        sa.Column("status", connection_status_enum, nullable=False, server_default="pending"),
        sa.Column("display_name", sa.String(length=255)),
        sa.Column("encrypted_auth_blob", sa.LargeBinary, nullable=False),
        sa.Column("scopes", postgresql.JSONB),
        sa.Column("metadata", postgresql.JSONB),
        sa.Column("last_synced_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.UniqueConstraint("org_id", "provider", "environment", name="uq_connections_scope"),
    )

    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("budget_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("budgets.id")),
        sa.Column("channel", alert_channel_enum, nullable=False),
        sa.Column("frequency", alert_frequency_enum, nullable=False),
        sa.Column("severity", alert_severity_enum, nullable=False, server_default="warning"),
        sa.Column("rule_json", postgresql.JSONB, nullable=False),
        sa.Column("quiet_hours_start", sa.Time(timezone=True)),
        sa.Column("quiet_hours_end", sa.Time(timezone=True)),
        sa.Column("debounce_minutes", sa.Integer, nullable=False, server_default="60"),
        sa.Column("max_alerts_per_day", sa.Integer, nullable=False, server_default="10"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
    )

    op.create_table(
        "raw_usage_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("connections.id")),
        sa.Column("provider", provider_enum, nullable=False),
        sa.Column("environment", environment_enum, nullable=False),
        sa.Column("metric", sa.String(length=255), nullable=False),
        sa.Column("unit", sa.String(length=64), nullable=False),
        sa.Column("quantity", sa.Numeric(20, 6), nullable=False),
        sa.Column("unit_cost", sa.Numeric(20, 6)),
        sa.Column("cost", sa.Numeric(20, 6)),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="usd"),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=50)),
        sa.Column("metadata", postgresql.JSONB),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
    )

    op.create_index(
        "ix_raw_usage_events_org_ts",
        "raw_usage_events",
        ["org_id", "ts"],
    )
    op.create_index(
        "ix_raw_usage_events_provider_ts",
        "raw_usage_events",
        ["provider", "ts"],
    )

    op.create_table(
        "daily_usage_costs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("provider", provider_enum, nullable=False),
        sa.Column("environment", environment_enum, nullable=False),
        sa.Column("day", sa.Date, nullable=False),
        sa.Column("quantity_sum", sa.Numeric(20, 6), nullable=False),
        sa.Column("cost_sum", sa.Numeric(20, 6), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="usd"),
        sa.Column("confidence_min", sa.Numeric(20, 6)),
        sa.Column("confidence_max", sa.Numeric(20, 6)),
        sa.UniqueConstraint(
            "org_id", "provider", "environment", "day", name="uq_daily_usage_scope"
        ),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("object_type", sa.String(length=64), nullable=False),
        sa.Column("object_id", sa.String(length=64)),
        sa.Column("metadata", postgresql.JSONB),
        sa.Column("ip_address", sa.String(length=64)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
    )

    op.create_index("ix_audit_log_org_created", "audit_log", ["org_id", "created_at"])

    op.execute(
        "SELECT create_hypertable('raw_usage_events', 'ts', if_not_exists => TRUE, migrate_data => TRUE);"
    )


def downgrade() -> None:
    op.drop_index("ix_audit_log_org_created", table_name="audit_log")
    op.drop_table("audit_log")
    op.drop_table("daily_usage_costs")
    op.drop_index("ix_raw_usage_events_provider_ts", table_name="raw_usage_events")
    op.drop_index("ix_raw_usage_events_org_ts", table_name="raw_usage_events")
    op.drop_table("raw_usage_events")
    op.drop_table("alerts")
    op.drop_table("connections")
    op.drop_table("budgets")
    op.drop_table("users")
    op.drop_table("orgs")

    alert_severity_enum.drop(op.get_bind(), checkfirst=True)
    alert_frequency_enum.drop(op.get_bind(), checkfirst=True)
    alert_channel_enum.drop(op.get_bind(), checkfirst=True)
    connection_status_enum.drop(op.get_bind(), checkfirst=True)
    environment_enum.drop(op.get_bind(), checkfirst=True)
    provider_enum.drop(op.get_bind(), checkfirst=True)
    user_role_enum.drop(op.get_bind(), checkfirst=True)
    plan_type_enum.drop(op.get_bind(), checkfirst=True)
