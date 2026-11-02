"""durable worker ownership and scheduling

Revision ID: d5772d41a928
Revises: dc3c10c4db8e
Create Date: 2026-11-02 11:42:13.039923

worker 心跳將故障回收與任務時間上限分開。部署已停止舊 worker, 但舊的 running 工作
仍可能留在表內, 因此先回收再移除租約。不可重試的 AI/回覆工作保守轉成死信,
避免遷移時重送未知結果的外部請求。新增必填欄位只在回填期間使用 server default。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'd5772d41a928'
down_revision: str | Sequence[str] | None = 'dc3c10c4db8e'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('background_workers',
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('heartbeat_at', sa.DateTime(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.CheckConstraint("status IN ('active', 'dead')", name=op.f('ck_background_workers_valid_status')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_background_workers'))
    )
    op.create_index('ix_background_workers_heartbeat', 'background_workers', ['status', 'heartbeat_at'], unique=False)
    op.drop_constraint(op.f('ck_background_jobs_valid_lease'), 'background_jobs', type_='check')
    op.drop_constraint(op.f('ck_background_jobs_valid_status'), 'background_jobs', type_='check')
    op.add_column('background_jobs', sa.Column('max_attempts', sa.Integer(), nullable=False, server_default='3'))
    op.add_column('background_jobs', sa.Column('queue', sa.String(length=50), nullable=False, server_default='general'))
    op.add_column('background_jobs', sa.Column('idempotency_key', sa.String(length=250), nullable=True))
    op.add_column('background_jobs', sa.Column('worker_id', sa.UUID(), nullable=True))
    op.add_column('background_jobs', sa.Column('last_error', sa.String(length=50), nullable=True))
    op.add_column('background_jobs', sa.Column('finished_at', sa.DateTime(), nullable=True))
    op.execute("UPDATE background_jobs SET max_attempts = 1 WHERE task_name IN ('product_drafts.prefill', 'line_collection.reply')")
    op.execute("""
        UPDATE background_jobs SET
            status = CASE WHEN status = 'failed' OR attempts >= max_attempts THEN 'dead' ELSE 'pending' END,
            finished_at = CASE WHEN status = 'failed' OR attempts >= max_attempts THEN COALESCE(updated_at, created_at) ELSE NULL END,
            last_error = CASE WHEN status = 'failed' THEN 'legacy_failure' ELSE 'worker_lost' END,
            lease_token = NULL
        WHERE status IN ('failed', 'running')
    """)
    op.alter_column('background_jobs', 'max_attempts', server_default=None)
    op.alter_column('background_jobs', 'queue', server_default=None)
    op.drop_index(op.f('ix_background_jobs_expired'), table_name='background_jobs')
    op.create_index('ix_background_jobs_worker', 'background_jobs', ['worker_id', 'status'], unique=False)
    op.create_unique_constraint(op.f('uq_background_jobs_task_name'), 'background_jobs', ['task_name', 'idempotency_key'])
    op.drop_column('background_jobs', 'locked_until')
    op.create_check_constraint('valid_status', 'background_jobs', "status IN ('pending', 'running', 'succeeded', 'dead')")
    op.create_check_constraint('positive_max_attempts', 'background_jobs', 'max_attempts >= 1')
    op.create_check_constraint('valid_owner', 'background_jobs', "(status = 'running' AND lease_token IS NOT NULL AND worker_id IS NOT NULL) OR (status <> 'running' AND lease_token IS NULL AND worker_id IS NULL)")
    op.execute('ALTER TABLE background_jobs SET (autovacuum_vacuum_scale_factor = 0.02, autovacuum_analyze_scale_factor = 0.02)')


def downgrade() -> None:
    op.drop_constraint(op.f('ck_background_jobs_valid_owner'), 'background_jobs', type_='check')
    op.drop_constraint(op.f('ck_background_jobs_positive_max_attempts'), 'background_jobs', type_='check')
    op.drop_constraint(op.f('ck_background_jobs_valid_status'), 'background_jobs', type_='check')
    op.execute("DELETE FROM background_jobs WHERE status = 'succeeded'")
    op.execute("UPDATE background_jobs SET status = CASE WHEN status = 'dead' THEN 'failed' WHEN status = 'running' THEN 'pending' ELSE status END, lease_token = NULL")
    op.add_column('background_jobs', sa.Column('locked_until', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
    op.drop_constraint(op.f('uq_background_jobs_task_name'), 'background_jobs', type_='unique')
    op.drop_index('ix_background_jobs_worker', table_name='background_jobs')
    op.create_index(op.f('ix_background_jobs_expired'), 'background_jobs', ['status', 'locked_until'], unique=False)
    op.drop_column('background_jobs', 'finished_at')
    op.drop_column('background_jobs', 'last_error')
    op.drop_column('background_jobs', 'worker_id')
    op.drop_column('background_jobs', 'idempotency_key')
    op.drop_column('background_jobs', 'queue')
    op.drop_column('background_jobs', 'max_attempts')
    op.create_check_constraint('valid_status', 'background_jobs', "status IN ('pending', 'running', 'failed')")
    op.create_check_constraint('valid_lease', 'background_jobs', "(status = 'running' AND lease_token IS NOT NULL AND locked_until IS NOT NULL) OR (status <> 'running' AND lease_token IS NULL AND locked_until IS NULL)")
    op.execute('ALTER TABLE background_jobs RESET (autovacuum_vacuum_scale_factor, autovacuum_analyze_scale_factor)')
    op.drop_index('ix_background_workers_heartbeat', table_name='background_workers')
    op.drop_table('background_workers')
