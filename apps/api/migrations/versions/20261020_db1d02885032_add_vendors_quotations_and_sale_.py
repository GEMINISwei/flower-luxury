"""add vendors quotations and sale snapshots

Revision ID: db1d02885032
Revises: 4c051833bb88
Create Date: 2026-10-20 23:25:09.042238

成交金額與成本獨立保存, 讓退回後重新報價不覆蓋歷史利潤.
永久國家鎖定避免刪除最後一筆詢價後改變廠商的計價規則.
同商品廠商唯一及目前成交的部分唯一索引提供併發寫入的最後防線.
僅新增資料表, 不修改既有商品或捏造舊成交紀錄, 不需要回填資料.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'db1d02885032'
down_revision: str | Sequence[str] | None = '4c051833bb88'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('vendors',
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('country', sa.String(), nullable=False),
    sa.Column('note', sa.String(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('country_locked', sa.Boolean(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.CheckConstraint("country IN ('TW', 'CN')", name=op.f('ck_vendors_vendor_country')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_vendors'))
    )
    op.create_index('uq_vendors_name_folded', 'vendors', [sa.literal_column('lower(name)')], unique=True)
    op.create_table('product_quotes',
    sa.Column('product_id', sa.UUID(), nullable=False),
    sa.Column('vendor_id', sa.UUID(), nullable=False),
    sa.Column('vendor_country', sa.String(), nullable=False),
    sa.Column('currency', sa.String(), nullable=False),
    sa.Column('original_amount', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('exchange_rate', sa.Numeric(precision=16, scale=6), nullable=False),
    sa.Column('amount_twd', sa.BigInteger(), nullable=False),
    sa.Column('note', sa.String(), nullable=True),
    sa.Column('revision', sa.Integer(), nullable=False),
    sa.Column('created_by', sa.String(), nullable=False),
    sa.Column('updated_by', sa.String(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.CheckConstraint("(vendor_country = 'TW' AND currency = 'TWD' AND exchange_rate = 1 AND original_amount = trunc(original_amount)) OR (vendor_country = 'CN' AND currency = 'CNY')", name=op.f('ck_product_quotes_quote_country_currency')),
    sa.CheckConstraint('amount_twd BETWEEN 0 AND 9007199254740991', name=op.f('ck_product_quotes_quote_twd_range')),
    sa.CheckConstraint('exchange_rate > 0', name=op.f('ck_product_quotes_quote_rate_positive')),
    sa.CheckConstraint('original_amount > 0', name=op.f('ck_product_quotes_quote_amount_positive')),
    sa.CheckConstraint('revision > 0', name=op.f('ck_product_quotes_quote_revision_positive')),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], name=op.f('fk_product_quotes_product_id_products'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['vendor_id'], ['vendors.id'], name=op.f('fk_product_quotes_vendor_id_vendors'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_product_quotes'))
    )
    op.create_index('ix_product_quotes_vendor_id', 'product_quotes', ['vendor_id'], unique=False)
    op.create_index('uq_product_quotes_product_vendor', 'product_quotes', ['product_id', 'vendor_id'], unique=True)
    op.create_table('product_sales',
    sa.Column('product_id', sa.UUID(), nullable=False),
    sa.Column('quote_id', sa.UUID(), nullable=False),
    sa.Column('vendor_id', sa.UUID(), nullable=False),
    sa.Column('vendor_name', sa.String(), nullable=False),
    sa.Column('vendor_country', sa.String(), nullable=False),
    sa.Column('currency', sa.String(), nullable=False),
    sa.Column('original_amount', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('exchange_rate', sa.Numeric(precision=16, scale=6), nullable=False),
    sa.Column('amount_twd', sa.BigInteger(), nullable=False),
    sa.Column('cost_price', sa.Integer(), nullable=False),
    sa.Column('profit_amount', sa.BigInteger(), nullable=False),
    sa.Column('is_current', sa.Boolean(), nullable=False),
    sa.Column('changed_by', sa.String(), nullable=False),
    sa.Column('operator_name', sa.String(), nullable=False),
    sa.Column('sold_at', sa.DateTime(), nullable=False),
    sa.Column('returned_at', sa.DateTime(), nullable=True),
    sa.Column('returned_by', sa.String(), nullable=True),
    sa.Column('return_reason', sa.String(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.CheckConstraint("(vendor_country = 'TW' AND currency = 'TWD' AND exchange_rate = 1 AND original_amount = trunc(original_amount)) OR (vendor_country = 'CN' AND currency = 'CNY')", name=op.f('ck_product_sales_sale_country_currency')),
    sa.CheckConstraint('(is_current AND returned_at IS NULL AND returned_by IS NULL AND return_reason IS NULL) OR (NOT is_current AND returned_at IS NOT NULL AND returned_by IS NOT NULL AND length(trim(return_reason)) > 0)', name=op.f('ck_product_sales_sale_return_fields')),
    sa.CheckConstraint('amount_twd BETWEEN 0 AND 9007199254740991', name=op.f('ck_product_sales_sale_twd_range')),
    sa.CheckConstraint('cost_price >= 0', name=op.f('ck_product_sales_sale_cost_nonnegative')),
    sa.CheckConstraint('original_amount > 0 AND exchange_rate > 0', name=op.f('ck_product_sales_sale_positive_amounts')),
    sa.CheckConstraint('profit_amount = amount_twd - cost_price', name=op.f('ck_product_sales_sale_profit_matches')),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], name=op.f('fk_product_sales_product_id_products'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['quote_id'], ['product_quotes.id'], name=op.f('fk_product_sales_quote_id_product_quotes'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['vendor_id'], ['vendors.id'], name=op.f('fk_product_sales_vendor_id_vendors'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_product_sales'))
    )
    op.create_index('ix_product_sales_quote_id', 'product_sales', ['quote_id'], unique=False)
    op.create_index('ix_product_sales_vendor_id', 'product_sales', ['vendor_id'], unique=False)
    op.create_index('uq_product_sales_current', 'product_sales', ['product_id'], unique=True, postgresql_where=sa.text('is_current'))


def downgrade() -> None:
    op.drop_index('uq_product_sales_current', table_name='product_sales', postgresql_where=sa.text('is_current'))
    op.drop_index('ix_product_sales_vendor_id', table_name='product_sales')
    op.drop_index('ix_product_sales_quote_id', table_name='product_sales')
    op.drop_table('product_sales')
    op.drop_index('uq_product_quotes_product_vendor', table_name='product_quotes')
    op.drop_index('ix_product_quotes_vendor_id', table_name='product_quotes')
    op.drop_table('product_quotes')
    op.drop_index('uq_vendors_name_folded', table_name='vendors')
    op.drop_table('vendors')
