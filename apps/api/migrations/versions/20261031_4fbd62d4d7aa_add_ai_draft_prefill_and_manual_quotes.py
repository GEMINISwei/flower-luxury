"""Preserve existing human edits while introducing optional AI draft prefill.

Temporary server defaults backfill existing drafts. Stored field keys are protected
as manual edits, including explicitly cleared values. Quotes remain draft data
until approval, and a singleton settings revision invalidates outdated AI results.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '4fbd62d4d7aa'
down_revision: str | Sequence[str] | None = '1ac89c038bcd'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('draft_prefill_settings',
    sa.Column('key', sa.String(length=16), nullable=False),
    sa.Column('supplement', sa.Text(), nullable=False),
    sa.Column('revision', sa.Integer(), nullable=False),
    sa.Column('updated_by', sa.String(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.CheckConstraint("key = 'global'", name=op.f('ck_draft_prefill_settings_prefill_global_only')),
    sa.CheckConstraint('revision >= 1', name=op.f('ck_draft_prefill_settings_prefill_settings_positive_revision')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_draft_prefill_settings')),
    sa.UniqueConstraint('key', name=op.f('uq_draft_prefill_settings_key'))
    )
    op.add_column('product_drafts', sa.Column('manual_fields', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column('product_drafts', sa.Column('quotes', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column('product_drafts', sa.Column('prefill_revision', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('product_drafts', sa.Column('prefill_status', sa.String(length=16), nullable=False, server_default='idle'))

    op.execute("""UPDATE product_drafts SET manual_fields = COALESCE(
        (SELECT jsonb_agg(key) FROM jsonb_object_keys(fields) AS key), '[]'::jsonb)""")
    for column in ('manual_fields', 'quotes', 'prefill_revision', 'prefill_status'):
        op.alter_column('product_drafts', column, server_default=None)
    op.create_check_constraint('prefill_positive_revision', 'product_drafts', 'prefill_revision >= 0')
    op.create_check_constraint('prefill_valid_status', 'product_drafts',
                              "prefill_status IN ('idle', 'disabled', 'queued', 'ready', 'failed')")


def downgrade() -> None:
    op.drop_constraint(op.f('ck_product_drafts_prefill_valid_status'), 'product_drafts', type_='check')
    op.drop_constraint(op.f('ck_product_drafts_prefill_positive_revision'), 'product_drafts', type_='check')
    op.drop_column('product_drafts', 'prefill_status')
    op.drop_column('product_drafts', 'prefill_revision')
    op.drop_column('product_drafts', 'quotes')
    op.drop_column('product_drafts', 'manual_fields')
    op.drop_table('draft_prefill_settings')
