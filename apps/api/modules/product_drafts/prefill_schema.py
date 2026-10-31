from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from modules.products.public import QuoteAmount, QuoteRate
from shared.http.schema import UuidText

from .schema import DraftFields


class PrefillContent(BaseModel):
    content: str


class PrefillJsonSchema(BaseModel):
    json_schema: dict[str, Any]


class PrefillApplication(BaseModel):
    applied: bool


class PrefillSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    supplement: str = Field(max_length=10000)
    revision: int = Field(ge=0)


class PrefillSettingsInfo(PrefillSettingsUpdate):
    configured: bool
    base_prompt: str


class PrefillPreview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=200000)
    supplement: str = Field(max_length=10000)


class PrefillVendorInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    vendor_id: UuidText
    original_amount: QuoteAmount
    exchange_rate: QuoteRate = Decimal(1)


class PrefillResult(DraftFields):
    vendor_info: list[PrefillVendorInfo] = Field(default_factory=list)
