"""add_level_and_correlation_to_execution_logs

Revision ID: a1b2c3d4e5f6
Revises: cd859b7730f3
Create Date: 2026-06-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'cd859b7730f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE execution_logs ADD COLUMN IF NOT EXISTS level VARCHAR(16) DEFAULT 'INFO'")
    op.execute("ALTER TABLE execution_logs ADD COLUMN IF NOT EXISTS correlation_id VARCHAR(64)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_execution_logs_correlation_id ON execution_logs (correlation_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_execution_logs_correlation_id")
    op.execute("ALTER TABLE execution_logs DROP COLUMN IF EXISTS correlation_id")
    op.execute("ALTER TABLE execution_logs DROP COLUMN IF EXISTS level")
