"""prepare user table for two-factor auth"""

from alembic import op
import sqlalchemy as sa


revision = "20251212043612"
down_revision = "20251211161924"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("two_factor_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("users", sa.Column("two_factor_secret", sa.LargeBinary()))


def downgrade() -> None:
    op.drop_column("users", "two_factor_secret")
    op.drop_column("users", "two_factor_enabled")
