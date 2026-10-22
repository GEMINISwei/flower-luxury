"""add catalog workflow and exchange rates

Revision ID: 4c051833bb88
Revises: 6573dd4efcb3
Create Date: 2026-10-19 23:36:06.345347

新增獨立資料表, 不搬移舊版資料. 品牌以不分大小寫的唯一索引防止重複,
商品外鍵禁止直接刪除被引用品牌. 匯率使用 Numeric 避免浮點誤差,
商品狀態與成本以資料庫約束阻擋不合法寫入. 既有資料表不變, 不需回填.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '4c051833bb88'
down_revision: str | Sequence[str] | None = '6573dd4efcb3'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('brands',
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_brands'))
    )
    op.create_index('uq_brands_name_folded', 'brands', [sa.literal_column('lower(name)')], unique=True)
    op.create_table('exchange_rate_settings',
    sa.Column('currency', sa.String(), nullable=False),
    sa.Column('rate', sa.Numeric(precision=16, scale=6), nullable=False),
    sa.Column('updated_by', sa.String(), nullable=False),
    sa.Column('operator_name', sa.String(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.CheckConstraint("currency = 'CNY'", name=op.f('ck_exchange_rate_settings_exchange_rate_cny_only')),
    sa.CheckConstraint('rate > 0', name=op.f('ck_exchange_rate_settings_exchange_rate_positive')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_exchange_rate_settings')),
    sa.UniqueConstraint('currency', name=op.f('uq_exchange_rate_settings_currency'))
    )
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
    sa.CheckConstraint("status IN ('not_acquired', 'in_stock', 'sold')", name=op.f('ck_products_product_status')),
    sa.CheckConstraint('cost_price >= 0', name=op.f('ck_products_product_cost_nonnegative')),
    sa.CheckConstraint('year IS NULL OR year BETWEEN 1 AND 9999', name=op.f('ck_products_product_year_range')),
    sa.ForeignKeyConstraint(['brand_id'], ['brands.id'], name=op.f('fk_products_brand_id_brands'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_products')),
    sa.UniqueConstraint('sku', name=op.f('uq_products_sku'))
    )
    op.create_index('ix_products_brand_id', 'products', ['brand_id'], unique=False)
    op.create_index('ix_products_created_at_id', 'products', ['created_at', 'id'], unique=False)
    op.create_index('ix_products_status', 'products', ['status'], unique=False)
    op.create_table('product_photos',
    sa.Column('product_id', sa.UUID(), nullable=False),
    sa.Column('storage_key', sa.String(), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.Column('uploaded_by', sa.String(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], name=op.f('fk_product_photos_product_id_products'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_product_photos')),
    sa.UniqueConstraint('storage_key', name=op.f('uq_product_photos_storage_key'))
    )
    op.create_index('ix_product_photos_product_id', 'product_photos', ['product_id'], unique=False)
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
    op.drop_index('ix_product_photos_product_id', table_name='product_photos')
    op.drop_table('product_photos')
    op.drop_index('ix_products_status', table_name='products')
    op.drop_index('ix_products_created_at_id', table_name='products')
    op.drop_index('ix_products_brand_id', table_name='products')
    op.drop_table('products')
    op.drop_table('exchange_rate_settings')
    op.drop_index('uq_brands_name_folded', table_name='brands')
    op.drop_table('brands')
