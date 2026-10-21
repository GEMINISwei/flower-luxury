"""simplify product statuses

Revision ID: 29e7062acabd
Revises: db1d02885032
Create Date: 2026-10-21

未成交商品統一歸未收購, 售出只由詢價成交觸發.
舊在庫資料及歷程的狀態一併映射, 保留原始事件時間、操作者與原因.
合併後不能推回哪些未收購原本是在庫, downgrade 只恢復可接受的狀態範圍.
Alembic autogenerate 不偵測 check constraint 的文字差異, 所以明確替換約束.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "29e7062acabd"
down_revision: str | Sequence[str] | None = "db1d02885032"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.text("UPDATE products SET status = 'not_acquired' WHERE status = 'in_stock'"))
    op.execute(sa.text("UPDATE product_status_history SET from_status = 'not_acquired' "
                       "WHERE from_status = 'in_stock'"))
    op.execute(sa.text("UPDATE product_status_history SET to_status = 'not_acquired' "
                       "WHERE to_status = 'in_stock'"))
    op.drop_constraint(op.f("ck_products_product_status"), "products", type_="check")
    op.create_check_constraint(op.f("ck_products_product_status"), "products",
                               "status IN ('not_acquired', 'sold')")


def downgrade() -> None:
    op.drop_constraint(op.f("ck_products_product_status"), "products", type_="check")
    op.create_check_constraint(op.f("ck_products_product_status"), "products",
                               "status IN ('not_acquired', 'in_stock', 'sold')")
