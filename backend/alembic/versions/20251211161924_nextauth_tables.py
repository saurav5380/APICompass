"""add nextauth tables and user profile fields"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20251211161924"
down_revision = "0007_local_connector_mode"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("name", sa.String(length=255)))
    op.add_column("users", sa.Column("image", sa.Text()))
    op.add_column("users", sa.Column("email_verified", sa.DateTime(timezone=True)))

    op.create_table(
        "accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(length=255), nullable=False),
        sa.Column("provider", sa.String(length=255), nullable=False),
        sa.Column("provider_account_id", sa.String(length=255), nullable=False),
        sa.Column("refresh_token", sa.Text()),
        sa.Column("access_token", sa.Text()),
        sa.Column("expires_at", sa.Integer()),
        sa.Column("token_type", sa.String(length=255)),
        sa.Column("scope", sa.Text()),
        sa.Column("id_token", sa.Text()),
        sa.Column("session_state", sa.String(length=255)),
        sa.Column("oauth_token_secret", sa.Text()),
        sa.Column("oauth_token", sa.Text()),
        sa.UniqueConstraint("provider", "provider_account_id", name="uq_accounts_provider_account_id"),
    )

    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_token", sa.String(length=255), nullable=False, unique=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expires", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "verification_tokens",
        sa.Column("identifier", sa.String(length=255), nullable=False),
        sa.Column("token", sa.String(length=255), nullable=False),
        sa.Column("expires", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("identifier", "token", name="pk_verification_tokens"),
        sa.UniqueConstraint("token"),
    )


def downgrade() -> None:
    op.drop_table("verification_tokens")
    op.drop_table("sessions")
    op.drop_table("accounts")
    op.drop_column("users", "email_verified")
    op.drop_column("users", "image")
    op.drop_column("users", "name")
