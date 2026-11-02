"""classify existing worker queues

Revision ID: a0183a058a19
Revises: d5772d41a928

既有工作先前都標成 general, 依現行任務分類回填, 讓部署後的積壓統計立即正確。
只改維運分類, 不改 payload、狀態或重試次數。
"""

from collections.abc import Sequence

from alembic import op

revision: str = "a0183a058a19"
down_revision: str | Sequence[str] | None = "d5772d41a928"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        UPDATE background_jobs SET queue = CASE
            WHEN task_name = 'line_collection.download' THEN 'downloads'
            WHEN task_name = 'product_drafts.prefill' THEN 'ai'
            WHEN task_name = 'line_collection.reply' THEN 'replies'
            WHEN task_name IN ('product_drafts.cleanup', 'product_drafts.expire_receipt',
                'line_collection.expire', 'line_collection.expire_reply',
                'system.cleanup_jobs') THEN 'maintenance'
            ELSE queue END
    """)


def downgrade() -> None:
    op.execute("UPDATE background_jobs SET queue = 'general'")
