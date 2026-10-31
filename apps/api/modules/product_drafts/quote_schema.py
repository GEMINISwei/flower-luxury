from decimal import Decimal
from typing import Any

from modules.products.public import QuoteCreate

from .schema import VersionRequest


class DraftQuoteUpdate(QuoteCreate, VersionRequest):
    def __init__(self, *, original_amount: Decimal | str | None = None, **data: Any) -> None:
        super().__init__(original_amount=original_amount, **data)
