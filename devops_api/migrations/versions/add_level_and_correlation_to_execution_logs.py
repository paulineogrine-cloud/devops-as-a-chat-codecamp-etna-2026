"""add level and correlation_id to execution_logs

Revision ID: a1b2c3d4e5f6
Revises: f8abc996ce80
Create Date: 2026-06-10
"""
from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "f8abc996ce80"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE execution_logs ADD COLUMN IF NOT EXISTS level VARCHAR(16) DEFAULT 'INFO'"
    )
    op.execute(
        "ALTER TABLE execution_logs ADD COLUMN IF NOT EXISTS correlation_id VARCHAR(64)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_execution_logs_correlation_id "
        "ON execution_logs (correlation_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_execution_logs_correlation_id")
    op.execute("ALTER TABLE execution_logs DROP COLUMN IF EXISTS correlation_id")
    op.execute("ALTER TABLE execution_logs DROP COLUMN IF EXISTS level")
