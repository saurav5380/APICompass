"""create alert events table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_alert_events"
down_revision = "0004_daily_usage_costs_ca"
branch_labels = None
depends_on = None

provider_enum = postgresql.ENUM(
    "openai", "twilio", "sendgrid", "stripe", "generic", name="provider_enum", create_type=False
)
environment_enum = postgresql.ENUM("prod", "staging", "dev", name="environment_enum", create_type=False)
alert_channel_enum = postgresql.ENUM("email", "slack", name="alert_channel_enum", create_type=False)
alert_severity_enum = postgresql.ENUM("info", "warning", "critical", name="alert_severity_enum", create_type=False)


def upgrade() -> None:
    op.create_table(
        "alert_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("budget_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("budgets.id", ondelete="SET NULL")),
        sa.Column("provider", provider_enum, nullable=True),
        sa.Column("environment", environment_enum, nullable=True),
        sa.Column("alert_type", sa.String(length=50), nullable=False),
        sa.Column("channel", alert_channel_enum, nullable=False),
        sa.Column("severity", alert_severity_enum, nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "triggered_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alert_events_org_time", "alert_events", ["org_id", "triggered_at"])


def downgrade() -> None:
    op.drop_index("ix_alert_events_org_time", table_name="alert_events")
    op.drop_table("alert_events")
