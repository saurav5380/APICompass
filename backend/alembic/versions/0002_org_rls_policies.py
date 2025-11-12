"""enforce row level security scoped by org"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002_org_rls_policies"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


ORG_SCOPED_TABLES = (
    "users",
    "connections",
    "budgets",
    "alerts",
    "raw_usage_events",
    "daily_usage_costs",
    "audit_log",
)

GUC_EXPRESSION = "current_setting('app.current_org_id', true)::uuid"


def _policy_name(table: str) -> str:
    return f"{table}_org_rls"


def upgrade() -> None:
    for table in ORG_SCOPED_TABLES:
        policy = _policy_name(table)
        op.execute(sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;"))
        op.execute(sa.text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;"))
        op.execute(sa.text(f"DROP POLICY IF EXISTS {policy} ON {table};"))
        op.execute(
            sa.text(
                f"""
                CREATE POLICY {policy}
                ON {table}
                USING (org_id = {GUC_EXPRESSION})
                WITH CHECK (org_id = {GUC_EXPRESSION});
                """
            )
        )


def downgrade() -> None:
    for table in ORG_SCOPED_TABLES:
        policy = _policy_name(table)
        op.execute(sa.text(f"DROP POLICY IF EXISTS {policy} ON {table};"))
        op.execute(sa.text(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;"))
        op.execute(sa.text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;"))
