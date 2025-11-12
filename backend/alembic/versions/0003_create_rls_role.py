"""create dedicated role for enforcing RLS"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0003_create_rls_role"
down_revision = "0002_org_rls_policies"
branch_labels = None
depends_on = None


ROLE_NAME = "apicompass_rls"


def upgrade() -> None:
    op.execute(
        sa.text(
            f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_roles WHERE rolname = '{ROLE_NAME}'
                ) THEN
                    CREATE ROLE {ROLE_NAME} NOLOGIN;
                END IF;
            END
            $$;
            """
        )
    )
    op.execute(sa.text(f"GRANT CONNECT ON DATABASE api_compass TO {ROLE_NAME};"))
    op.execute(sa.text(f"GRANT USAGE ON SCHEMA public TO {ROLE_NAME};"))
    op.execute(
        sa.text(
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {ROLE_NAME};"
        )
    )
    op.execute(
        sa.text(
            f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {ROLE_NAME};"
        )
    )
    op.execute(
        sa.text(
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {ROLE_NAME};"
        )
    )
    op.execute(
        sa.text(
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO {ROLE_NAME};"
        )
    )
    op.execute(sa.text(f"GRANT {ROLE_NAME} TO postgres;"))


def downgrade() -> None:
    op.execute(
        sa.text(
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM {ROLE_NAME};"
        )
    )
    op.execute(
        sa.text(
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE USAGE, SELECT ON SEQUENCES FROM {ROLE_NAME};"
        )
    )
    op.execute(
        sa.text(
            f"REVOKE SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public FROM {ROLE_NAME};"
        )
    )
    op.execute(
        sa.text(
            f"REVOKE USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public FROM {ROLE_NAME};"
        )
    )
    op.execute(sa.text(f"REVOKE {ROLE_NAME} FROM postgres;"))
    op.execute(sa.text(f"REVOKE USAGE ON SCHEMA public FROM {ROLE_NAME};"))
    op.execute(sa.text(f"REVOKE CONNECT ON DATABASE api_compass FROM {ROLE_NAME};"))
    op.execute(sa.text(f"DROP ROLE IF EXISTS {ROLE_NAME};"))
