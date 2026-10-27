"""add product photos

Revision ID: d546ef79e085
Revises: 0449214ae25b
Create Date: 2026-10-27 20:50:13.828643

照片顯示檔與原圖分開保存, 原圖欄位沿用舊版名稱與可空設計, 供後續搬移歷史照片.
完整性約束要求原圖路徑, 名稱及媒體類型同時有值或同時為空, 避免不完整的下載資料.
本次只新增照片表, 不修改商品欄位或既有 migration, 不搬移資料與檔案.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'd546ef79e085'
down_revision: str | Sequence[str] | None = '0449214ae25b'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('product_photos',
    sa.Column('product_id', sa.UUID(), nullable=False),
    sa.Column('storage_key', sa.String(), nullable=False),
    sa.Column('original_storage_key', sa.String(), nullable=True),
    sa.Column('original_filename', sa.String(), nullable=True),
    sa.Column('original_media_type', sa.String(), nullable=True),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.Column('uploaded_by', sa.String(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.CheckConstraint('(original_storage_key IS NULL AND original_filename IS NULL AND original_media_type IS NULL) OR (original_storage_key IS NOT NULL AND original_filename IS NOT NULL AND original_media_type IS NOT NULL)', name=op.f('ck_product_photos_original_complete')),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], name=op.f('fk_product_photos_product_id_products'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_product_photos')),
    sa.UniqueConstraint('original_storage_key', name=op.f('uq_product_photos_original_storage_key')),
    sa.UniqueConstraint('storage_key', name=op.f('uq_product_photos_storage_key'))
    )
    op.create_index('ix_product_photos_product_id', 'product_photos', ['product_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_product_photos_product_id', table_name='product_photos')
    op.drop_table('product_photos')
