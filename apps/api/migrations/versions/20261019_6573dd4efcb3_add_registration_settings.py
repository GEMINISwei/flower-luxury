"""add registration settings

Revision ID: 6573dd4efcb3
Revises: 959dc24d48e4
Create Date: 2026-10-19 20:20:08.977966

共用註冊碼由店長在後台更換, 必須跨重啟保存且只存摘要。
固定唯一鍵與 check constraint 保證只有一組設定; 空表代表尚未開放註冊。
新增獨立資料表, 不改動或回填既有帳號與角色。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '6573dd4efcb3'
down_revision: str | Sequence[str] | None = '959dc24d48e4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('registration_settings',
    sa.Column('code', sa.String(), nullable=False),
    sa.Column('key_hash', sa.String(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.CheckConstraint("code = 'signup'", name=op.f('ck_registration_settings_registration_settings_singleton')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_registration_settings')),
    sa.UniqueConstraint('code', name=op.f('uq_registration_settings_code'))
    )


def downgrade() -> None:
    op.drop_table('registration_settings')
