"""buffer LINE events before grouping

Revision ID: f3aa10b5ce4a
Revises: 6b3603f89d78
Create Date: 2026-11-01 23:18:20.374252

收件先保存原文與照片, 三分鐘穩定窗口後才依原始時間分組.
異常內容保留供人工處理, 既有批次與商品不重寫.
新增來源等待時間允許 NULL, 既有來源不會被當成待處理工作.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'f3aa10b5ce4a'
down_revision: str | Sequence[str] | None = '6b3603f89d78'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('product_draft_buffered_events',
    sa.Column('source_key', sa.String(length=200), nullable=False),
    sa.Column('kind', sa.String(length=10), nullable=False),
    sa.Column('occurred_at', sa.DateTime(), nullable=False),
    sa.Column('message_id', sa.UUID(), nullable=True),
    sa.Column('status', sa.String(length=10), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.CheckConstraint("kind IN ('message', 'start', 'end')", name=op.f('ck_product_draft_buffered_events_buffer_event_kind')),
    sa.CheckConstraint("status IN ('pending', 'issue')", name=op.f('ck_product_draft_buffered_events_buffer_event_status')),
    sa.ForeignKeyConstraint(['message_id'], ['product_draft_messages.id'], name=op.f('fk_product_draft_buffered_events_message_id_product_draft_messages'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['source_key'], ['product_draft_streams.source_key'], name=op.f('fk_product_draft_buffered_events_source_key_product_draft_streams')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_product_draft_buffered_events')),
    sa.UniqueConstraint('message_id', name=op.f('uq_product_draft_buffered_events_message_id'))
    )
    op.create_index('ix_product_draft_buffer_source_status_time', 'product_draft_buffered_events', ['source_key', 'status', 'occurred_at'], unique=False)
    op.add_column('product_draft_streams', sa.Column('buffer_until', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('product_draft_streams', 'buffer_until')
    op.drop_index('ix_product_draft_buffer_source_status_time', table_name='product_draft_buffered_events')
    op.drop_table('product_draft_buffered_events')
