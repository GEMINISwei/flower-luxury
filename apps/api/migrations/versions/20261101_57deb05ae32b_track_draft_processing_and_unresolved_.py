"""track draft processing and unresolved collection messages

Revision ID: 57deb05ae32b
Revises: f3aa10b5ce4a
Create Date: 2026-11-01 23:44:20.254065

將來源整理中與未解決異常狀態同步到商品, 供列表篩選與建檔鎖定使用.
既有商品回填 false, 避免新增非空欄位阻擋升級; 回填後移除暫時的資料庫預設值.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '57deb05ae32b'
down_revision: str | Sequence[str] | None = 'f3aa10b5ce4a'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('product_drafts', sa.Column('processing', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('product_drafts', sa.Column('needs_confirmation', sa.Boolean(), nullable=False, server_default=sa.false()))

    op.alter_column('product_drafts', 'processing', server_default=None)
    op.alter_column('product_drafts', 'needs_confirmation', server_default=None)


def downgrade() -> None:
    op.drop_column('product_drafts', 'needs_confirmation')
    op.drop_column('product_drafts', 'processing')
