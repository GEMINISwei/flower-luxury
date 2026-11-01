"""select vendor sale on draft approval

Revision ID: dc3c10c4db8e
Revises: 57deb05ae32b
Create Date: 2026-11-02 00:07:39.871347

暫存只保存人工選定的報價識別, 審核時才建立正式成交快照.
既有暫存維持未選取, 不從 AI 或最高報價推測成交廠商.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'dc3c10c4db8e'
down_revision: str | Sequence[str] | None = '57deb05ae32b'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('product_drafts', sa.Column('selected_quote_id', sa.String(length=200), nullable=True))


def downgrade() -> None:
    op.drop_column('product_drafts', 'selected_quote_id')
