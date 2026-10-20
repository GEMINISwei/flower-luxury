from decimal import Decimal
from typing import Annotated, Any

from pydantic import BaseModel, Field

from shared.http.schema import UtcDateTime


class ExchangeRateUpdate(BaseModel):
    rate: Annotated[Decimal, Field(gt=0, max_digits=16, decimal_places=6, allow_inf_nan=False)]


    def __init__(self, *, rate: Decimal | str | None = None, **data: Any) -> None:
        super().__init__(rate=rate, **data)


class ExchangeRateSettings(BaseModel):
    currency: str = "CNY"
    base_currency: str = "TWD"
    rate: Decimal | None = None
    updated_by: str | None = None
    operator_name: str | None = None
    updated_at: UtcDateTime | None = None
