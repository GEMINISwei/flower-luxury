"""Keep LINE membership and collection consent separate from product drafts.

Hashed event and message receipts prevent redelivery after discard or unsend without
retaining message content. Draft receipts retain the approved product identifier
so unsending a moved message can still request manual review. The new nullable
column requires no backfill. Message links use SET NULL so draft deletion does not
remove the short-lived redelivery protection.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '9de05a4696fe'
down_revision: str | Sequence[str] | None = '9a66169aabd8'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("product_draft_receipts", sa.Column("approved_product_id", sa.String(), nullable=True))
    op.create_table('line_event_receipts',
    sa.Column('fingerprint', sa.String(length=64), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_line_event_receipts')),
    sa.UniqueConstraint('fingerprint', name=op.f('uq_line_event_receipts_fingerprint'))
    )
    op.create_index(op.f('ix_line_event_receipts_expires_at'), 'line_event_receipts', ['expires_at'], unique=False)
    op.create_table('line_groups',
    sa.Column('group_id', sa.String(length=200), nullable=False),
    sa.Column('name', sa.String(), nullable=True),
    sa.Column('enabled', sa.Boolean(), nullable=False),
    sa.Column('joined', sa.Boolean(), nullable=False),
    sa.Column('last_membership_at', sa.DateTime(), nullable=True),
    sa.Column('collect_from', sa.DateTime(), nullable=True),
    sa.Column('review_product_id', sa.String(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_line_groups')),
    sa.UniqueConstraint('group_id', name=op.f('uq_line_groups_group_id'))
    )
    op.create_index('ix_line_groups_created_at_id', 'line_groups', ['created_at', 'id'], unique=False)
    op.create_table('line_message_links',
    sa.Column('group_id', sa.UUID(), nullable=False),
    sa.Column('fingerprint', sa.String(length=64), nullable=False),
    sa.Column('external_id', sa.String(length=200), nullable=True),
    sa.Column('message_id', sa.UUID(), nullable=True),
    sa.Column('draft_id', sa.String(), nullable=True),
    sa.Column('revoked', sa.Boolean(), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['group_id'], ['line_groups.id'], name=op.f('fk_line_message_links_group_id_line_groups'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['message_id'], ['product_draft_messages.id'], name=op.f('fk_line_message_links_message_id_product_draft_messages'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_line_message_links')),
    sa.UniqueConstraint('fingerprint', name=op.f('uq_line_message_links_fingerprint'))
    )
    op.create_index(op.f('ix_line_message_links_expires_at'), 'line_message_links', ['expires_at'], unique=False)


def downgrade() -> None:
    op.drop_column("product_draft_receipts", "approved_product_id")
    op.drop_index(op.f('ix_line_message_links_expires_at'), table_name='line_message_links')
    op.drop_table('line_message_links')
    op.drop_index('ix_line_groups_created_at_id', table_name='line_groups')
    op.drop_table('line_groups')
    op.drop_index(op.f('ix_line_event_receipts_expires_at'), table_name='line_event_receipts')
    op.drop_table('line_event_receipts')
