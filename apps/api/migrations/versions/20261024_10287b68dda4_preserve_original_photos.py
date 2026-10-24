"""preserve original photos

Revision ID: 10287b68dda4
Revises: 29e7062acabd

舊照片只保存顯示檔, 無法回填原圖. 原圖欄位允許整組為 NULL, 保留舊路徑與照片識別碼;
新照片則必須一起保存原圖路徑、下載檔名與 MIME, 避免下載指到不完整的檔案資料.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "10287b68dda4"
down_revision: str | Sequence[str] | None = "29e7062acabd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("product_photos", sa.Column("original_storage_key", sa.String(), nullable=True))
    op.add_column("product_photos", sa.Column("original_filename", sa.String(), nullable=True))
    op.add_column("product_photos", sa.Column("original_media_type", sa.String(), nullable=True))
    op.create_unique_constraint(op.f("uq_product_photos_original_storage_key"),
                                "product_photos", ["original_storage_key"])
    op.create_check_constraint(
        "ck_product_photos_original_complete", "product_photos",
        "(original_storage_key IS NULL AND original_filename IS NULL "
        "AND original_media_type IS NULL) OR (original_storage_key IS NOT NULL "
        "AND original_filename IS NOT NULL AND original_media_type IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_product_photos_original_complete", "product_photos", type_="check")
    op.drop_constraint(op.f("uq_product_photos_original_storage_key"),
                       "product_photos", type_="unique")
    op.drop_column("product_photos", "original_media_type")
    op.drop_column("product_photos", "original_filename")
    op.drop_column("product_photos", "original_storage_key")
