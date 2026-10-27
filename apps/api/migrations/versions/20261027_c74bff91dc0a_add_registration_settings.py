"""add registration settings

Revision ID: c74bff91dc0a
Revises: 959dc24d48e4
Create Date: 2026-10-27 18:24:51.668783

沿用舊版註冊設定欄位與約束, 讓之後搬移資料時不必重新對應同義欄位。
空表代表尚未設定註冊碼, 不提供任何預設碼或回填既有帳號。
只建立新的設定表, 不變更既有使用者、角色或初始 migration。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'c74bff91dc0a'
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
