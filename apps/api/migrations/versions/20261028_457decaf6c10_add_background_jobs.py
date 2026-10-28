"""add background jobs

Revision ID: 457decaf6c10
Revises: 77910ea2b576
Create Date: 2026-10-28 21:39:38.992010

佇列與業務資料共用 PostgreSQL 交易, 避免資料回滾後工作仍執行。
持有 token 與期限保護重啟後的重領, 約束避免半套持有狀態。
這是新增的空表, 不需要資料回填, 也不修改既有商品資料。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '457decaf6c10'
down_revision: str | Sequence[str] | None = '77910ea2b576'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('background_jobs',
    sa.Column('task_name', sa.String(length=200), nullable=False),
    sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('available_at', sa.DateTime(), nullable=False),
    sa.Column('locked_until', sa.DateTime(), nullable=True),
    sa.Column('lease_token', sa.UUID(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.CheckConstraint("(status = 'running' AND lease_token IS NOT NULL AND locked_until IS NOT NULL) OR (status <> 'running' AND lease_token IS NULL AND locked_until IS NULL)", name=op.f('ck_background_jobs_valid_lease')),
    sa.CheckConstraint("status IN ('pending', 'running', 'failed')", name=op.f('ck_background_jobs_valid_status')),
    sa.CheckConstraint('attempts >= 0', name=op.f('ck_background_jobs_nonnegative_attempts')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_background_jobs'))
    )
    op.create_index('ix_background_jobs_expired', 'background_jobs', ['status', 'locked_until'], unique=False)
    op.create_index('ix_background_jobs_ready', 'background_jobs', ['status', 'available_at', 'id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_background_jobs_ready', table_name='background_jobs')
    op.drop_index('ix_background_jobs_expired', table_name='background_jobs')
    op.drop_table('background_jobs')
