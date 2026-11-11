"""保存預填嘗試次數, 避免工作歷史到期後再次啟動已耗盡的商品.

Revision ID: acb67612100f
Revises: 440a6b9963bd
Create Date: 2026-11-11 22:47:42.227453

舊資料先以零回填, 背景恢復工作會採用仍存在的工作次數; 已成功商品不重跑.
暫時的 server default 只用於回填, 新增商品仍由 ORM 提供預設值.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'acb67612100f'
down_revision: str | Sequence[str] | None = '440a6b9963bd'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('product_drafts', sa.Column('prefill_attempts', sa.Integer(),
                                            server_default=sa.text('0'), nullable=False))
    op.alter_column('product_drafts', 'prefill_attempts', server_default=None)
    op.create_check_constraint(op.f('ck_product_drafts_prefill_attempt_limit'),
                               'product_drafts', 'prefill_attempts BETWEEN 0 AND 3')


def downgrade() -> None:
    op.drop_constraint(op.f('ck_product_drafts_prefill_attempt_limit'), 'product_drafts',
                       type_='check')
    op.drop_column('product_drafts', 'prefill_attempts')
