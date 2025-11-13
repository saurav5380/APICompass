"""support daily usage cost aggregation indexes"""

from alembic import op

revision = "0004_daily_usage_costs_ca"
down_revision = "0003_create_rls_role"
branch_labels = None
depends_on = None

INDEX_NAME = "ix_daily_usage_costs_org_day"


def upgrade() -> None:
    op.create_index(
        INDEX_NAME,
        "daily_usage_costs",
        ["org_id", "provider", "environment", "day"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="daily_usage_costs")
