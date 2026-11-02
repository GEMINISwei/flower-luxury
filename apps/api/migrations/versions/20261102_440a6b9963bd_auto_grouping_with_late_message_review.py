"""Group LINE receipts automatically and keep late messages for manual review.

Manual rounds and finalization are replaced by original-time intervals: closed
drafts keep their fields, AI results and photos, ungrouped receipts are grouped
with the same image-then-text rule, and receipts inside a closed interval become
pending messages of that draft. Receipts outside every interval are dropped,
matching how new late messages are handled. Drafts that never reached AI because
they waited for finalization are queued once.
"""

import json
from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Connection

revision: str = '440a6b9963bd'
down_revision: str | Sequence[str] | None = '1dd77096672e'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _intervals(connection: Connection) -> dict[str, list[dict[str, Any]]]:
    drafts = connection.execute(sa.text("""
        SELECT d.id, d.source_key, d.collecting,
               COALESCE(min(m.occurred_at) FILTER (WHERE m.kind = 'image'),
                        min(m.occurred_at), d.received_at) AS started_at,
               min(m.occurred_at) FILTER (WHERE m.kind = 'text') AS first_text_at,
               COALESCE(max(m.occurred_at), d.received_at) AS last_at
        FROM product_drafts d LEFT JOIN product_draft_messages m ON m.draft_id = d.id
        GROUP BY d.id ORDER BY d.source_key, 4, d.id
    """)).mappings().all()
    by_source: dict[str, list[dict[str, Any]]] = {}
    for row in drafts:
        by_source.setdefault(row["source_key"], []).append(dict(row))
    for rows in by_source.values():
        for index, row in enumerate(rows):
            following = rows[index + 1]["started_at"] if index + 1 < len(rows) else None
            row["ended_at"] = following or (None if row["collecting"] else
                                            row["last_at"] + timedelta(microseconds=1))
            row["collecting"] = row["ended_at"] is None
    return by_source


def _new_draft(connection: Connection, source: str, started_at: datetime) -> dict[str, Any]:
    row = {"id": uuid4(), "source_key": source, "started_at": started_at,
           "first_text_at": None, "ended_at": None, "collecting": True}
    connection.execute(sa.text("""
        INSERT INTO product_drafts (id, source_key, received_at, collecting, version, fields,
            manual_fields, quotes, prefill_revision, prefill_status, has_text, created_at)
        VALUES (:id, :source, :at, FALSE, 1, '{}', '[]', '[]', 0, 'idle', FALSE,
                timezone('utc', now()))
    """), {"id": row["id"], "source": source, "at": started_at})
    return row


def _assign(connection: Connection, message: Any, draft: UUID, *, pending: bool) -> None:
    connection.execute(sa.text("""
        UPDATE product_draft_messages SET draft_id = :draft, pending = :pending WHERE id = :id
    """), {"draft": draft, "pending": pending, "id": message["id"]})
    connection.execute(sa.text("""
        UPDATE product_draft_photos SET draft_id = :draft WHERE message_id = :id
    """), {"draft": None if pending else draft, "id": message["id"]})


def _place(connection: Connection, rows: list[dict[str, Any]], message: Any) -> None:
    time, kind = message["occurred_at"], message["kind"]
    inside = [row for row in rows if row["started_at"] <= time
              and (row["ended_at"] is None or time < row["ended_at"])]
    current = inside[-1] if inside else None
    if current and current["collecting"]:
        if kind == "image" and current["first_text_at"] and time > current["first_text_at"]:
            current["ended_at"], current["collecting"] = time, False
            rows.append(_new_draft(connection, message["source_key"], time))
            _assign(connection, message, rows[-1]["id"], pending=False)
            return
        if kind == "text":
            current["first_text_at"] = min(current["first_text_at"] or time, time)
        _assign(connection, message, current["id"], pending=False)
    elif current:
        _assign(connection, message, current["id"], pending=True)
    elif kind == "image" and not any(row["started_at"] > time for row in rows):
        for row in rows:
            if row["collecting"]:
                row["ended_at"], row["collecting"] = time, False
        rows.append(_new_draft(connection, message["source_key"], time))
        _assign(connection, message, rows[-1]["id"], pending=False)
    else:
        connection.execute(sa.text("DELETE FROM product_draft_messages WHERE id = :id"),
                           {"id": message["id"]})


def convert_to_auto_grouping(connection: Connection) -> None:
    by_source = _intervals(connection)
    # 每個來源只能有一件收集中, 先全部關閉, 算完區間再打開最後一件.
    connection.execute(sa.text("UPDATE product_drafts SET collecting = FALSE"))
    loose = connection.execute(sa.text("""
        SELECT id, source_key, kind, occurred_at FROM product_draft_messages
        WHERE draft_id IS NULL ORDER BY source_key, occurred_at, sequence, id
    """)).mappings().all()
    for message in loose:
        _place(connection, by_source.setdefault(message["source_key"], []), message)
    for rows in by_source.values():
        for row in rows:
            connection.execute(sa.text("""
                UPDATE product_drafts SET collecting = :collecting, version = version + 1
                WHERE id = :id
            """), {"collecting": row["collecting"], "id": row["id"]})
            connection.execute(sa.text("""
                INSERT INTO product_draft_intervals
                    (id, source_key, draft_key, started_at, first_text_at, ended_at, created_at)
                VALUES (:id, :source, :key, :started, :text, :ended, timezone('utc', now()))
            """), {"id": uuid4(), "source": row["source_key"], "key": str(row["id"]),
                   "started": row["started_at"], "text": row["first_text_at"],
                   "ended": row["ended_at"]})
    connection.execute(sa.text("""
        UPDATE product_drafts d SET has_text = EXISTS (SELECT 1 FROM product_draft_messages m
            WHERE m.draft_id = d.id AND m.kind = 'text' AND m.pending IS FALSE),
            main_photo_id = COALESCE(d.main_photo_id, (SELECT p.id FROM product_draft_photos p
                WHERE p.draft_id = d.id ORDER BY p.id LIMIT 1))
    """))


def _queue_missing_prefill(connection: Connection) -> None:
    waiting = connection.execute(sa.text("""
        SELECT id FROM product_drafts WHERE collecting IS FALSE AND prefill_revision = 0
    """)).scalars().all()
    for id in waiting:
        connection.execute(sa.text("""
            UPDATE product_drafts SET prefill_revision = 1, prefill_status = 'queued',
                finalized_at = COALESCE(finalized_at, timezone('utc', now())) WHERE id = :id
        """), {"id": id})
        connection.execute(sa.text("""
            INSERT INTO background_jobs (id, task_name, payload, status, attempts, max_attempts,
                queue, available_at, created_at)
            VALUES (:job, 'product_drafts.prefill', CAST(:payload AS jsonb), 'pending', 0, 1,
                    'ai', timezone('utc', now()), timezone('utc', now()))
        """), {"job": uuid4(), "payload": json.dumps({"draft_id": str(id), "revision": 1})})


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('product_draft_intervals',
    sa.Column('source_key', sa.String(length=200), nullable=False),
    sa.Column('draft_key', sa.String(length=200), nullable=False),
    sa.Column('started_at', sa.DateTime(), nullable=False),
    sa.Column('first_text_at', sa.DateTime(), nullable=True),
    sa.Column('ended_at', sa.DateTime(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['source_key'], ['product_draft_streams.source_key'], name=op.f('fk_product_draft_intervals_source_key_product_draft_streams')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_product_draft_intervals')),
    sa.UniqueConstraint('draft_key', name=op.f('uq_product_draft_intervals_draft_key'))
    )
    op.create_index('ix_product_draft_intervals_source_start', 'product_draft_intervals', ['source_key', 'started_at'], unique=False)
    op.add_column('product_draft_messages', sa.Column('pending', sa.Boolean(), nullable=False,
                                                      server_default=sa.false()))
    op.alter_column('product_draft_messages', 'pending', server_default=None)
    op.drop_index(op.f('ix_product_draft_batch_issues_source'), table_name='product_draft_batch_issues')
    op.drop_table('product_draft_batch_issues')
    op.drop_index(op.f('ix_product_draft_buffer_source_status_time'), table_name='product_draft_buffered_events')
    op.drop_table('product_draft_buffered_events')
    op.drop_index(op.f('ix_product_draft_windows_batch_start'), table_name='product_draft_windows')
    op.drop_table('product_draft_windows')
    op.drop_index(op.f('ix_product_draft_batches_source_start'), table_name='product_draft_batches')
    op.drop_index(op.f('uq_product_draft_batches_active_source'), table_name='product_draft_batches', postgresql_where='(ended_at IS NULL)')
    op.drop_table('product_draft_batches')
    op.drop_constraint(op.f('fk_product_draft_messages_collection_id_product_draft_c_fe3c'), 'product_draft_messages', type_='foreignkey')
    op.drop_column('product_draft_messages', 'collection_id')
    op.drop_column('product_draft_streams', 'last_control_at')
    op.drop_column('product_draft_streams', 'buffer_until')
    op.drop_constraint(op.f('fk_product_drafts_collection_id_product_draft_collections'), 'product_drafts', type_='foreignkey')
    op.drop_column('product_drafts', 'collection_id')
    op.drop_column('product_drafts', 'processing')
    op.drop_column('product_drafts', 'needs_confirmation')
    op.drop_index(op.f('uq_product_draft_collections_collecting_source'), table_name='product_draft_collections', postgresql_where="((status)::text = 'collecting'::text)")
    op.drop_table('product_draft_collections')
    connection = op.get_bind()
    convert_to_auto_grouping(connection)
    _queue_missing_prefill(connection)
    op.execute("DELETE FROM background_jobs WHERE task_name = 'product_drafts.buffer'")


def downgrade() -> None:
    # Deployment rejects rollback across this migration: pending late messages and
    # automatic intervals have no manual-round equivalent.
    op.add_column('product_drafts', sa.Column('needs_confirmation', sa.BOOLEAN(), autoincrement=False, nullable=False))
    op.add_column('product_drafts', sa.Column('processing', sa.BOOLEAN(), autoincrement=False, nullable=False))
    op.add_column('product_drafts', sa.Column('collection_id', sa.UUID(), autoincrement=False, nullable=True))
    op.create_foreign_key(op.f('fk_product_drafts_collection_id_product_draft_collections'), 'product_drafts', 'product_draft_collections', ['collection_id'], ['id'])
    op.add_column('product_draft_streams', sa.Column('buffer_until', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
    op.add_column('product_draft_streams', sa.Column('last_control_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
    op.add_column('product_draft_messages', sa.Column('collection_id', sa.UUID(), autoincrement=False, nullable=True))
    op.create_foreign_key(op.f('fk_product_draft_messages_collection_id_product_draft_c_fe3c'), 'product_draft_messages', 'product_draft_collections', ['collection_id'], ['id'])
    op.drop_column('product_draft_messages', 'pending')
    op.create_table('product_draft_windows',
    sa.Column('batch_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('draft_key', sa.VARCHAR(length=200), autoincrement=False, nullable=False),
    sa.Column('started_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column('last_image_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column('first_text_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('ended_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['batch_id'], ['product_draft_batches.id'], name=op.f('fk_product_draft_windows_batch_id_product_draft_batches'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_product_draft_windows')),
    sa.UniqueConstraint('draft_key', name=op.f('uq_product_draft_windows_draft_key'), postgresql_include=[], postgresql_nulls_not_distinct=False)
    )
    op.create_index(op.f('ix_product_draft_windows_batch_start'), 'product_draft_windows', ['batch_id', 'started_at'], unique=False)
    op.create_table('product_draft_collections',
    sa.Column('source_key', sa.VARCHAR(length=200), autoincrement=False, nullable=False),
    sa.Column('status', sa.VARCHAR(length=16), autoincrement=False, nullable=False),
    sa.Column('first_event_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column('last_event_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column('completed_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.CheckConstraint("status::text = ANY (ARRAY['collecting'::character varying, 'confirmation'::character varying, 'finalized'::character varying]::text[])", name=op.f('ck_product_draft_collections_valid_status')),
    sa.ForeignKeyConstraint(['source_key'], ['product_draft_streams.source_key'], name=op.f('fk_product_draft_collections_source_key_product_draft_streams')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_product_draft_collections'))
    )
    op.create_index(op.f('uq_product_draft_collections_collecting_source'), 'product_draft_collections', ['source_key'], unique=True, postgresql_where="((status)::text = 'collecting'::text)")
    op.create_table('product_draft_batches',
    sa.Column('source_key', sa.VARCHAR(length=200), autoincrement=False, nullable=False),
    sa.Column('started_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column('ended_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('latest_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['source_key'], ['product_draft_streams.source_key'], name=op.f('fk_product_draft_batches_source_key_product_draft_streams')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_product_draft_batches'))
    )
    op.create_index(op.f('uq_product_draft_batches_active_source'), 'product_draft_batches', ['source_key'], unique=True, postgresql_where='(ended_at IS NULL)')
    op.create_index(op.f('ix_product_draft_batches_source_start'), 'product_draft_batches', ['source_key', 'started_at'], unique=False)
    op.create_table('product_draft_buffered_events',
    sa.Column('source_key', sa.VARCHAR(length=200), autoincrement=False, nullable=False),
    sa.Column('kind', sa.VARCHAR(length=10), autoincrement=False, nullable=False),
    sa.Column('occurred_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column('message_id', sa.UUID(), autoincrement=False, nullable=True),
    sa.Column('status', sa.VARCHAR(length=10), autoincrement=False, nullable=False),
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.CheckConstraint("kind::text = ANY (ARRAY['message'::character varying, 'start'::character varying, 'end'::character varying]::text[])", name=op.f('ck_product_draft_buffered_events_buffer_event_kind')),
    sa.CheckConstraint("status::text = ANY (ARRAY['pending'::character varying, 'issue'::character varying]::text[])", name=op.f('ck_product_draft_buffered_events_buffer_event_status')),
    sa.ForeignKeyConstraint(['message_id'], ['product_draft_messages.id'], name=op.f('fk_product_draft_buffered_events_message_id_product_dra_5c9c'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['source_key'], ['product_draft_streams.source_key'], name=op.f('fk_product_draft_buffered_events_source_key_product_dra_ff70')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_product_draft_buffered_events')),
    sa.UniqueConstraint('message_id', name=op.f('uq_product_draft_buffered_events_message_id'), postgresql_include=[], postgresql_nulls_not_distinct=False)
    )
    op.create_index(op.f('ix_product_draft_buffer_source_status_time'), 'product_draft_buffered_events', ['source_key', 'status', 'occurred_at'], unique=False)
    op.create_table('product_draft_batch_issues',
    sa.Column('source_key', sa.VARCHAR(length=200), autoincrement=False, nullable=False),
    sa.Column('occurred_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column('reason', sa.VARCHAR(length=30), autoincrement=False, nullable=False),
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['source_key'], ['product_draft_streams.source_key'], name=op.f('fk_product_draft_batch_issues_source_key_product_draft_streams')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_product_draft_batch_issues'))
    )
    op.create_index(op.f('ix_product_draft_batch_issues_source'), 'product_draft_batch_issues', ['source_key'], unique=False)
    op.drop_index('ix_product_draft_intervals_source_start', table_name='product_draft_intervals')
    op.drop_table('product_draft_intervals')
    # ### end Alembic commands ###
