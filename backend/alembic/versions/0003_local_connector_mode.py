"""add local connector columns to connections"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0003_local_connector_mode"
down_revision = "0002_org_rls_policies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "connections",
        sa.Column(
            "local_connector_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "connections",
        sa.Column(
            "local_agent_last_seen_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("connections", "local_agent_last_seen_at")
    op.drop_column("connections", "local_connector_enabled")
