from sqlalchemy import Index, func
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.table import BaseTable


class BrandTable(BaseTable):
    __tablename__ = "brands"

    name: Mapped[str] = mapped_column()
    is_active: Mapped[bool] = mapped_column(default=True)

    __table_args__ = (Index("uq_brands_name_folded", func.lower(name), unique=True),)
