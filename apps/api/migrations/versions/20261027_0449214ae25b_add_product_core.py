"""add product core

Revision ID: 0449214ae25b
Revises: 900b3c8b176f
Create Date: 2026-10-27 20:14:26.658017

沿用舊版商品與狀態歷程欄位, 包含尚未啟用的主圖欄位, 讓後續資料搬移不必重新對應.
狀態約束直接使用舊版最後的未收購與已出售兩種值, 不重演舊環境的在庫狀態轉換.
只新增商品及歷程, 不搬移舊資料, 不改動前兩階段 migration.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0449214ae25b'
down_revision: str | Sequence[str] | None = '900b3c8b176f'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('products',
    sa.Column('sku', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('brand_id', sa.UUID(), nullable=False),
    sa.Column('category', sa.String(), nullable=False),
    sa.Column('model_name', sa.String(), nullable=True),
    sa.Column('serial_number', sa.String(), nullable=True),
    sa.Column('color', sa.String(), nullable=True),
    sa.Column('year', sa.Integer(), nullable=True),
    sa.Column('cost_price', sa.Integer(), nullable=False),
    sa.Column('internal_note', sa.String(), nullable=True),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('main_photo_id', sa.String(), nullable=True),
    sa.Column('created_by', sa.String(), nullable=False),
    sa.Column('updated_by', sa.String(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.CheckConstraint("status IN ('not_acquired', 'sold')", name=op.f('ck_products_product_status')),
    sa.CheckConstraint('cost_price >= 0', name=op.f('ck_products_product_cost_nonnegative')),
    sa.CheckConstraint('year IS NULL OR year BETWEEN 1 AND 9999', name=op.f('ck_products_product_year_range')),
    sa.ForeignKeyConstraint(['brand_id'], ['brands.id'], name=op.f('fk_products_brand_id_brands'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_products')),
    sa.UniqueConstraint('sku', name=op.f('uq_products_sku'))
    )
    op.create_index('ix_products_brand_id', 'products', ['brand_id'], unique=False)
    op.create_index('ix_products_created_at_id', 'products', ['created_at', 'id'], unique=False)
    op.create_index('ix_products_status', 'products', ['status'], unique=False)
    op.create_table('product_status_history',
    sa.Column('product_id', sa.UUID(), nullable=False),
    sa.Column('from_status', sa.String(), nullable=True),
    sa.Column('to_status', sa.String(), nullable=False),
    sa.Column('action', sa.String(), nullable=False),
    sa.Column('reason', sa.String(), nullable=True),
    sa.Column('changed_by', sa.String(), nullable=False),
    sa.Column('operator_name', sa.String(), nullable=False),
    sa.Column('changed_at', sa.DateTime(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], name=op.f('fk_product_status_history_product_id_products'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_product_status_history'))
    )
    op.create_index('ix_product_status_history_product_id', 'product_status_history', ['product_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_product_status_history_product_id', table_name='product_status_history')
    op.drop_table('product_status_history')
    op.drop_index('ix_products_status', table_name='products')
    op.drop_index('ix_products_created_at_id', table_name='products')
    op.drop_index('ix_products_brand_id', table_name='products')
    op.drop_table('products')
