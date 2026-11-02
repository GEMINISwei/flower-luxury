"""Adopt unfinished receipts without rerunning completed work.

Legacy reviewed drafts retain their fields and AI results. Open drafts become
confirmation groups, and ungrouped receipts become a manual collection round.
"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Connection

revision: str = '1dd77096672e'
down_revision: str | Sequence[str] | None = 'a0183a058a19'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def adopt_collection_state(connection: Connection) -> None:
    connection.execute(sa.text("""
        UPDATE product_drafts SET finalized_at = COALESCE(finalized_at, timezone('utc', now())),
            processing = FALSE, version = version + 1
        WHERE collection_id IS NULL AND collecting IS FALSE
    """))
    opened = connection.execute(sa.text("""
        SELECT d.id, d.source_key, COALESCE(min(m.occurred_at), d.received_at) AS first,
               COALESCE(max(m.occurred_at), d.received_at) AS last
        FROM product_drafts d LEFT JOIN product_draft_messages m ON m.draft_id = d.id
        WHERE d.collection_id IS NULL AND d.collecting IS TRUE GROUP BY d.id
    """)).mappings().all()
    for draft in opened:
        round_id = uuid4()
        connection.execute(sa.text("""
            INSERT INTO product_draft_collections
                (id, source_key, status, first_event_at, last_event_at, completed_at, created_at)
            VALUES (:id, :source, 'confirmation', :first, :last,
                    timezone('utc', now()), timezone('utc', now()))
        """), {"id": round_id, "source": draft["source_key"], "first": draft["first"], "last": draft["last"]})
        connection.execute(sa.text("""
            UPDATE product_drafts SET collection_id = :round, collecting = FALSE, processing = FALSE,
                version = version + 1 WHERE id = :id
        """), {"round": round_id, "id": draft["id"]})
        connection.execute(sa.text("""
            UPDATE product_draft_messages SET collection_id = :round WHERE draft_id = :id
        """), {"round": round_id, "id": draft["id"]})
    sources = connection.execute(sa.text("""
        SELECT m.source_key, min(m.occurred_at) AS first, max(m.occurred_at) AS last
        FROM product_draft_messages m JOIN product_draft_buffered_events e ON e.message_id = m.id
        WHERE m.draft_id IS NULL AND m.collection_id IS NULL AND e.status = 'pending'
        GROUP BY m.source_key
    """)).mappings().all()
    for source in sources:
        round_id = uuid4()
        connection.execute(sa.text("""
            INSERT INTO product_draft_collections
                (id, source_key, status, first_event_at, last_event_at, created_at)
            VALUES (:id, :source, 'collecting', :first, :last, timezone('utc', now()))
        """), {"id": round_id, "source": source["source_key"],
                  "first": source["first"], "last": source["last"]})
        connection.execute(sa.text("""
            UPDATE product_draft_messages SET collection_id = :round
            WHERE source_key = :source AND draft_id IS NULL AND collection_id IS NULL
                AND id IN (SELECT message_id FROM product_draft_buffered_events WHERE status = 'pending')
        """), {"round": round_id, "source": source["source_key"]})
    connection.execute(sa.text("UPDATE product_draft_streams SET buffer_until = NULL"))
    connection.execute(sa.text("""
        UPDATE product_draft_batches SET ended_at = latest_at WHERE ended_at IS NULL
    """))
    connection.execute(sa.text("""
        DELETE FROM background_jobs WHERE task_name IN
            ('product_drafts.buffer', 'line_collection.reply', 'line_collection.expire_reply')
    """))


def upgrade() -> None:
    op.create_table('product_draft_collections',
    sa.Column('source_key', sa.String(length=200), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('first_event_at', sa.DateTime(), nullable=False),
    sa.Column('last_event_at', sa.DateTime(), nullable=False),
    sa.Column('completed_at', sa.DateTime(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.CheckConstraint("status IN ('collecting', 'confirmation', 'finalized')", name=op.f('ck_product_draft_collections_valid_status')),
    sa.ForeignKeyConstraint(['source_key'], ['product_draft_streams.source_key'], name=op.f('fk_product_draft_collections_source_key_product_draft_streams')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_product_draft_collections'))
    )
    op.create_index('uq_product_draft_collections_collecting_source', 'product_draft_collections', ['source_key'], unique=True, postgresql_where=sa.text("status = 'collecting'"))
    op.drop_table('line_command_replies')
    op.add_column('product_draft_messages', sa.Column('collection_id', sa.UUID(), nullable=True))
    op.create_foreign_key(op.f('fk_product_draft_messages_collection_id_product_draft_collections'), 'product_draft_messages', 'product_draft_collections', ['collection_id'], ['id'])
    op.add_column('product_drafts', sa.Column('collection_id', sa.UUID(), nullable=True))
    op.add_column('product_drafts', sa.Column('finalized_at', sa.DateTime(), nullable=True))
    op.add_column('product_drafts', sa.Column('finalized_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.create_foreign_key(op.f('fk_product_drafts_collection_id_product_draft_collections'), 'product_drafts', 'product_draft_collections', ['collection_id'], ['id'])

    op.drop_constraint(op.f('ck_product_drafts_prefill_valid_status'), 'product_drafts', type_='check')
    op.create_check_constraint(op.f('ck_product_drafts_prefill_valid_status'), 'product_drafts',
        "prefill_status IN ('idle', 'disabled', 'queued', 'ready', 'failed', 'unknown')")
    op.drop_constraint(op.f('ck_product_draft_photos_valid_status'), 'product_draft_photos', type_='check')
    op.create_check_constraint(op.f('ck_product_draft_photos_valid_status'), 'product_draft_photos',
        "status IN ('pending', 'stored', 'ready', 'failed')")
    op.create_check_constraint(op.f('ck_product_draft_photos_stored_original'), 'product_draft_photos',
        "status <> 'stored' OR original_key IS NOT NULL")
    adopt_collection_state(op.get_bind())


def downgrade() -> None:
    # Deployment rejects rollback across this migration: raw receipts cannot be un-finalized safely.
    op.execute("UPDATE product_drafts SET prefill_status = 'failed' WHERE prefill_status = 'unknown'")
    op.execute("UPDATE product_draft_photos SET status = 'pending' WHERE status = 'stored'")
    op.drop_constraint(op.f('ck_product_draft_photos_stored_original'), 'product_draft_photos', type_='check')
    op.drop_constraint(op.f('ck_product_draft_photos_valid_status'), 'product_draft_photos', type_='check')
    op.create_check_constraint(op.f('ck_product_draft_photos_valid_status'), 'product_draft_photos',
        "status IN ('pending', 'ready', 'failed')")
    op.drop_constraint(op.f('ck_product_drafts_prefill_valid_status'), 'product_drafts', type_='check')
    op.create_check_constraint(op.f('ck_product_drafts_prefill_valid_status'), 'product_drafts',
        "prefill_status IN ('idle', 'disabled', 'queued', 'ready', 'failed')")
    op.drop_constraint(op.f('fk_product_drafts_collection_id_product_draft_collections'), 'product_drafts', type_='foreignkey')
    op.drop_column('product_drafts', 'finalized_snapshot')
    op.drop_column('product_drafts', 'finalized_at')
    op.drop_column('product_drafts', 'collection_id')
    op.drop_constraint(op.f('fk_product_draft_messages_collection_id_product_draft_collections'), 'product_draft_messages', type_='foreignkey')
    op.drop_column('product_draft_messages', 'collection_id')
    op.create_table('line_command_replies',
    sa.Column('group_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('reply_token', sa.VARCHAR(length=200), autoincrement=False, nullable=False),
    sa.Column('text', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('expires_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['group_id'], ['line_groups.id'], name=op.f('fk_line_command_replies_group_id_line_groups'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_line_command_replies'))
    )
    op.drop_index('uq_product_draft_collections_collecting_source', table_name='product_draft_collections', postgresql_where=sa.text("status = 'collecting'"))
    op.drop_table('product_draft_collections')
