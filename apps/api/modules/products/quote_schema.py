from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

from shared.http.schema import SimpleListResponse, UtcDateTime, UuidText

type QuoteAmount = Annotated[Decimal, Field(
    gt=0, max_digits=12, decimal_places=2, allow_inf_nan=False,
)]


class QuoteUpdate(BaseModel):
    original_amount: QuoteAmount
    note: str | None = None

    def __init__(self, *, original_amount: Decimal | str | None = None, **data: Any) -> None:
        super().__init__(original_amount=original_amount, **data)


class QuoteCreate(QuoteUpdate):
    vendor_id: UuidText

    def __init__(self, *, original_amount: Decimal | str | None = None, **data: Any) -> None:
        super().__init__(original_amount=original_amount, **data)


class QuoteAmounts(BaseModel):
    currency: Literal["TWD", "CNY"]
    exchange_rate: Decimal
    amount_twd: int


class QuoteInfo(QuoteCreate, QuoteAmounts):
    id: str
    product_id: str
    vendor_name: str
    vendor_country: Literal["TW", "CN"]
    revision: int
    has_sales: bool
    created_at: UtcDateTime
    updated_at: UtcDateTime | None = None


class QuoteList(SimpleListResponse[QuoteInfo]):
    pass


class SaleCreate(BaseModel):
    quote_id: UuidText
    quote_revision: Annotated[int, Field(ge=1)]
    cost_price: Annotated[int, Field(ge=0, le=2147483647)]


class SaleInfo(QuoteAmounts):
    id: str
    product_id: str
    quote_id: str
    vendor_id: str
    vendor_name: str
    vendor_country: Literal["TW", "CN"]
    original_amount: Decimal
    cost_price: int
    profit_amount: int
    is_current: bool
    changed_by: str
    operator_name: str
    sold_at: UtcDateTime
    returned_at: UtcDateTime | None = None
    returned_by: str | None = None
    return_reason: str | None = None


class SaleList(SimpleListResponse[SaleInfo]):
    pass
