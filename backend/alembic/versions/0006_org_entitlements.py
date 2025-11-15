"""create org entitlements table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006_org_entitlements"
down_revision = "0005_alert_events"
branch_labels = None
depends_on = None

plan_enum = postgresql.ENUM("free", "pro", "enterprise", name="plan_type_enum", create_type=False)


def upgrade() -> None:
    op.create_table(
        "org_entitlements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("plan", plan_enum, nullable=False, server_default="free"),
        sa.Column("max_providers", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("sync_interval_minutes", sa.Integer(), nullable=False, server_default="1440"),
        sa.Column("digest_frequency", sa.String(length=20), nullable=False, server_default="weekly"),
        sa.Column("alerts_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("tips_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_price_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_status", sa.String(length=50), nullable=False, server_default="inactive"),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", name="uq_org_entitlements_org_id"),
    )

    bind = op.get_bind()
    org_rows = list(bind.execute(sa.text("SELECT id, plan FROM orgs")))
    for row in org_rows:
        plan = row.plan or "free"
        max_providers = 3 if plan == "pro" else 1
        sync_interval = 60 if plan == "pro" else 1440
        digest_frequency = "daily" if plan == "pro" else "weekly"
        feature_enabled = plan == "pro"
        bind.execute(
            sa.text(
                """
                INSERT INTO org_entitlements (
                    id,
                    org_id,
                    plan,
                    max_providers,
                    sync_interval_minutes,
                    digest_frequency,
                    alerts_enabled,
                    tips_enabled,
                    stripe_status,
                    created_at,
                    updated_at
                )
                VALUES (
                    gen_random_uuid(),
                    :org_id,
                    :plan,
                    :max_providers,
                    :sync_interval,
                    :digest_frequency,
                    :feature_enabled,
                    :feature_enabled,
                    'inactive',
                    timezone('utc', now()),
                    timezone('utc', now())
                )
                """
            ),
            {
                "org_id": row.id,
                "plan": plan,
                "max_providers": max_providers,
                "sync_interval": sync_interval,
                "digest_frequency": digest_frequency,
                "feature_enabled": feature_enabled,
            },
        )


def downgrade() -> None:
    op.drop_table("org_entitlements")
