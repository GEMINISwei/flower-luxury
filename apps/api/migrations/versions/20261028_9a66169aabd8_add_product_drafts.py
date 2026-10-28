"""add product drafts

Revision ID: 9a66169aabd8
Revises: 457decaf6c10
Create Date: 2026-10-28 22:43:16.314307

暫存與正式商品分表, 允許尚未完整的欄位並在放棄時硬刪除原始內容。
來源列鎖與部分唯一索引保證每個群組至多一筆收集中商品。
審核對照保留正式商品與審核者, 防重送摘要獨立保存並到期清除。
本次只新增空表, 不回填或改寫既有商品。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '9a66169aabd8'
down_revision: str | Sequence[str] | None = '457decaf6c10'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('product_draft_receipts',
    sa.Column('fingerprint', sa.String(length=64), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_product_draft_receipts')),
    sa.UniqueConstraint('fingerprint', name=op.f('uq_product_draft_receipts_fingerprint'))
    )
    op.create_index(op.f('ix_product_draft_receipts_expires_at'), 'product_draft_receipts', ['expires_at'], unique=False)
    op.create_table('product_draft_streams',
    sa.Column('source_key', sa.String(length=200), nullable=False),
    sa.Column('last_occurred_at', sa.DateTime(), nullable=True),
    sa.Column('next_sequence', sa.Integer(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_product_draft_streams')),
    sa.UniqueConstraint('source_key', name=op.f('uq_product_draft_streams_source_key'))
    )
    op.create_table('product_drafts',
    sa.Column('source_key', sa.String(length=200), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('fields', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('collecting', sa.Boolean(), nullable=False),
    sa.Column('has_text', sa.Boolean(), nullable=False),
    sa.Column('main_photo_id', sa.Uuid(), nullable=True),
    sa.Column('updated_by', sa.String(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.CheckConstraint('version >= 1', name=op.f('ck_product_drafts_positive_version')),
    sa.ForeignKeyConstraint(['source_key'], ['product_draft_streams.source_key'], name=op.f('fk_product_drafts_source_key_product_draft_streams')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_product_drafts'))
    )
    op.create_index('ix_product_drafts_created_at_id', 'product_drafts', ['created_at', 'id'], unique=False)
    op.create_index('uq_product_drafts_collecting_source', 'product_drafts', ['source_key'], unique=True, postgresql_where=sa.text('collecting IS TRUE'))
    op.create_table('product_draft_approvals',
    sa.Column('product_id', sa.UUID(), nullable=False),
    sa.Column('sku', sa.String(), nullable=False),
    sa.Column('reviewed_by', sa.String(), nullable=False),
    sa.Column('reviewer_name', sa.String(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], name=op.f('fk_product_draft_approvals_product_id_products'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_product_draft_approvals')),
    sa.UniqueConstraint('product_id', name=op.f('uq_product_draft_approvals_product_id'))
    )
    op.create_table('product_draft_messages',
    sa.Column('source_key', sa.String(length=200), nullable=False),
    sa.Column('draft_id', sa.UUID(), nullable=True),
    sa.Column('external_id', sa.String(length=200), nullable=False),
    sa.Column('kind', sa.String(length=8), nullable=False),
    sa.Column('text', sa.Text(), nullable=True),
    sa.Column('sender_id', sa.String(), nullable=True),
    sa.Column('sender_name', sa.String(), nullable=True),
    sa.Column('occurred_at', sa.DateTime(), nullable=False),
    sa.Column('sequence', sa.Integer(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.CheckConstraint("(kind = 'text' AND text IS NOT NULL) OR (kind = 'image' AND text IS NULL)", name=op.f('ck_product_draft_messages_matching_content')),
    sa.ForeignKeyConstraint(['draft_id'], ['product_drafts.id'], name=op.f('fk_product_draft_messages_draft_id_product_drafts'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['source_key'], ['product_draft_streams.source_key'], name=op.f('fk_product_draft_messages_source_key_product_draft_streams')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_product_draft_messages'))
    )
    op.create_index('ix_product_draft_messages_created_at_id', 'product_draft_messages', ['created_at', 'id'], unique=False)
    op.create_index('ix_product_draft_messages_draft_order', 'product_draft_messages', ['draft_id', 'occurred_at', 'sequence'], unique=False)
    op.create_table('product_draft_photos',
    sa.Column('draft_id', sa.UUID(), nullable=True),
    sa.Column('message_id', sa.UUID(), nullable=False),
    sa.Column('status', sa.String(length=8), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.Column('original_key', sa.String(), nullable=True),
    sa.Column('display_key', sa.String(), nullable=True),
    sa.Column('filename', sa.String(), nullable=True),
    sa.Column('extension', sa.String(), nullable=True),
    sa.Column('media_type', sa.String(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.CheckConstraint("status <> 'ready' OR (original_key IS NOT NULL AND display_key IS NOT NULL AND filename IS NOT NULL AND extension IS NOT NULL AND media_type IS NOT NULL)", name=op.f('ck_product_draft_photos_ready_files')),
    sa.CheckConstraint("status IN ('pending', 'ready', 'failed')", name=op.f('ck_product_draft_photos_valid_status')),
    sa.ForeignKeyConstraint(['draft_id'], ['product_drafts.id'], name=op.f('fk_product_draft_photos_draft_id_product_drafts'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['message_id'], ['product_draft_messages.id'], name=op.f('fk_product_draft_photos_message_id_product_draft_messages'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_product_draft_photos')),
    sa.UniqueConstraint('message_id', name=op.f('uq_product_draft_photos_message_id'))
    )
    op.create_index('ix_product_draft_photos_draft_order', 'product_draft_photos', ['draft_id', 'sort_order'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_product_draft_photos_draft_order', table_name='product_draft_photos')
    op.drop_table('product_draft_photos')
    op.drop_index('ix_product_draft_messages_draft_order', table_name='product_draft_messages')
    op.drop_index('ix_product_draft_messages_created_at_id', table_name='product_draft_messages')
    op.drop_table('product_draft_messages')
    op.drop_table('product_draft_approvals')
    op.drop_index('uq_product_drafts_collecting_source', table_name='product_drafts', postgresql_where=sa.text('collecting IS TRUE'))
    op.drop_index('ix_product_drafts_created_at_id', table_name='product_drafts')
    op.drop_table('product_drafts')
    op.drop_table('product_draft_streams')
    op.drop_index(op.f('ix_product_draft_receipts_expires_at'), table_name='product_draft_receipts')
    op.drop_table('product_draft_receipts')
