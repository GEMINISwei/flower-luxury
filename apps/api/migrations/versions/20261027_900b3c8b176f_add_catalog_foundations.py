"""add catalog foundations

Revision ID: 900b3c8b176f
Revises: c74bff91dc0a
Create Date: 2026-10-27 19:32:49.609605

沿用舊版品牌、廠商與人民幣匯率的表名、欄位、型別與約束, 避免之後搬資料時對應失準。
匯率不填預設值, 廠商國家鎖定欄位保留給後續詢價功能使用。
只新增三張業務資料表, 不變更既有帳號與註冊設定, 不包含舊資料搬移。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '900b3c8b176f'
down_revision: str | Sequence[str] | None = 'c74bff91dc0a'
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


def downgrade() -> None:
    op.drop_index('uq_vendors_name_folded', table_name='vendors')
    op.drop_table('vendors')
    op.drop_table('exchange_rate_settings')
    op.drop_index('uq_brands_name_folded', table_name='brands')
    op.drop_table('brands')
