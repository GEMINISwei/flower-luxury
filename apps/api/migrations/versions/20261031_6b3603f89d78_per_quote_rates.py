"""Detach quote rates from vendor countries without rewriting financial snapshots.

Draft quotes did not store rates, so backfill them before removing the old source.
Rename the permanent quote-history flag instead of recreating it. Legacy quote and
sale country/currency columns remain nullable archives; new records use explicit rates.
The removed vendor country and global setting cannot be reconstructed on downgrade.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Connection

revision: str = "6b3603f89d78"
down_revision: str | Sequence[str] | None = "4fbd62d4d7aa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def backfill_draft_quote_rates(connection: Connection) -> None:
    countries = {str(row.id): row.country for row in
                 connection.execute(sa.text("SELECT id, country FROM vendors"))}
    rate = connection.execute(sa.text("SELECT rate FROM exchange_rate_settings LIMIT 1")).scalar()
    statement = sa.text("UPDATE product_drafts SET quotes = :quotes WHERE id = :id").bindparams(
        sa.bindparam("quotes", type_=postgresql.JSONB()), sa.bindparam("id", type_=sa.Uuid()))
    for row in connection.execute(sa.text("SELECT id, quotes FROM product_drafts")).mappings():
        quotes = row["quotes"] or []
        for quote in quotes:
            if quote.get("exchange_rate") is not None:
                continue
            country = countries.get(quote["vendor_id"])
            if country == "CN" and rate is None:
                raise RuntimeError("中國廠商的暫存報價需要現有系統匯率，請先設定後再升級。")
            quote["exchange_rate"] = str(rate) if country == "CN" else "1"
        connection.execute(statement, {"id": row["id"], "quotes": quotes})


def upgrade() -> None:
    backfill_draft_quote_rates(op.get_bind())
    # 舊的逐訊息任務不能在新一輪收集結束後, 被誤認成同一修訂的工作.
    op.execute("DELETE FROM background_jobs WHERE task_name = 'product_drafts.prefill'")
    op.execute("""UPDATE product_drafts SET
        prefill_revision = CASE WHEN collecting THEN 0 ELSE greatest(prefill_revision, 1) END,
        prefill_status = CASE WHEN collecting THEN 'idle'
            WHEN prefill_status = 'queued' THEN 'failed' ELSE prefill_status END""")
    op.drop_table("exchange_rate_settings")
    for table, constraint in (("product_quotes", "quote_country_currency"),
                              ("product_sales", "sale_country_currency")):
        op.drop_constraint(op.f(f"ck_{table}_{constraint}"), table, type_="check")
        for column in ("vendor_country", "currency"):
            op.alter_column(table, column, existing_type=sa.String(), nullable=True)
    op.alter_column("vendors", "country_locked", new_column_name="has_quotes",
                    existing_type=sa.Boolean(), existing_nullable=False)
    op.drop_constraint(op.f("ck_vendors_vendor_country"), "vendors", type_="check")
    op.drop_column("vendors", "country")


def downgrade() -> None:
    raise RuntimeError("逐筆匯率已取代廠商國家與系統匯率，請往前修正或還原升級前備份。")
