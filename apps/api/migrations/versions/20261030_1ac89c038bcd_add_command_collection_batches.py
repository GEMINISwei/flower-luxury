"""Add explicit collection batches without discarding existing draft content.

Revision ID: 1ac89c038bcd
Revises: 9de05a4696fe

商品歸屬時間獨立保存, 讓審核與放棄後仍能識別晚到事件.
舊資料先回填收件時間, 再增加非空約束; 切換後舊暫存結束收集, 等待新指令.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '1ac89c038bcd'
down_revision: str | Sequence[str] | None = '9de05a4696fe'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('line_command_replies',
    sa.Column('group_id', sa.UUID(), nullable=False),
    sa.Column('reply_token', sa.String(length=200), nullable=False),
    sa.Column('text', sa.String(), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['group_id'], ['line_groups.id'], name=op.f('fk_line_command_replies_group_id_line_groups'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_line_command_replies'))
    )
    op.create_table('product_draft_batch_issues',
    sa.Column('source_key', sa.String(length=200), nullable=False),
    sa.Column('occurred_at', sa.DateTime(), nullable=False),
    sa.Column('reason', sa.String(length=30), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['source_key'], ['product_draft_streams.source_key'], name=op.f('fk_product_draft_batch_issues_source_key_product_draft_streams')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_product_draft_batch_issues'))
    )
    op.create_index('ix_product_draft_batch_issues_source', 'product_draft_batch_issues', ['source_key'], unique=False)
    op.create_table('product_draft_batches',
    sa.Column('source_key', sa.String(length=200), nullable=False),
    sa.Column('started_at', sa.DateTime(), nullable=False),
    sa.Column('ended_at', sa.DateTime(), nullable=True),
    sa.Column('latest_at', sa.DateTime(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['source_key'], ['product_draft_streams.source_key'], name=op.f('fk_product_draft_batches_source_key_product_draft_streams')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_product_draft_batches'))
    )
    op.create_index('ix_product_draft_batches_source_start', 'product_draft_batches', ['source_key', 'started_at'], unique=False)
    op.create_index('uq_product_draft_batches_active_source', 'product_draft_batches', ['source_key'], unique=True, postgresql_where=sa.text('ended_at IS NULL'))
    op.create_table('product_draft_windows',
    sa.Column('batch_id', sa.UUID(), nullable=False),
    sa.Column('draft_key', sa.String(length=200), nullable=False),
    sa.Column('started_at', sa.DateTime(), nullable=False),
    sa.Column('last_image_at', sa.DateTime(), nullable=False),
    sa.Column('first_text_at', sa.DateTime(), nullable=True),
    sa.Column('ended_at', sa.DateTime(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['batch_id'], ['product_draft_batches.id'], name=op.f('fk_product_draft_windows_batch_id_product_draft_batches'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_product_draft_windows')),
    sa.UniqueConstraint('draft_key', name=op.f('uq_product_draft_windows_draft_key'))
    )
    op.create_index('ix_product_draft_windows_batch_start', 'product_draft_windows', ['batch_id', 'started_at'], unique=False)
    op.add_column('line_groups', sa.Column('reply_failed', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.alter_column('line_groups', 'reply_failed', server_default=None)
    op.add_column('product_draft_streams', sa.Column('last_control_at', sa.DateTime(), nullable=True))
    op.add_column('product_drafts', sa.Column('received_at', sa.DateTime(), nullable=True))
    op.execute(sa.text("""
        UPDATE product_drafts AS draft SET received_at = COALESCE(
            (SELECT MIN(message.occurred_at) FROM product_draft_messages AS message
             WHERE message.draft_id = draft.id AND message.kind = 'image'), draft.created_at)
    """))
    op.alter_column('product_drafts', 'received_at', nullable=False)
    op.execute(sa.text("""
        UPDATE product_drafts SET collecting = false, version = version + 1,
            updated_at = CURRENT_TIMESTAMP AT TIME ZONE 'UTC' WHERE collecting = true
    """))
    op.execute(sa.text("""
        UPDATE product_draft_streams SET last_control_at = CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
    """))
    op.create_index('ix_product_drafts_received_at_id', 'product_drafts', ['received_at', 'id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_product_drafts_received_at_id', table_name='product_drafts')
    op.drop_column('product_drafts', 'received_at')
    op.drop_column('product_draft_streams', 'last_control_at')
    op.drop_column('line_groups', 'reply_failed')
    op.drop_index('ix_product_draft_windows_batch_start', table_name='product_draft_windows')
    op.drop_table('product_draft_windows')
    op.drop_index('uq_product_draft_batches_active_source', table_name='product_draft_batches', postgresql_where=sa.text('ended_at IS NULL'))
    op.drop_index('ix_product_draft_batches_source_start', table_name='product_draft_batches')
    op.drop_table('product_draft_batches')
    op.drop_index('ix_product_draft_batch_issues_source', table_name='product_draft_batch_issues')
    op.drop_table('product_draft_batch_issues')
    op.drop_table('line_command_replies')
