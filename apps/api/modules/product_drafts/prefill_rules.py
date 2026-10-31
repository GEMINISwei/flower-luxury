import json
from collections.abc import Iterable
from typing import Any, Protocol

from modules.products.public import price_quote
from shared.http.errors import LangException

from .prefill_schema import PrefillContent, PrefillJsonSchema, PrefillResult
from .schema import DraftFields

MAX_INPUT_CHARACTERS = 200000
MIN_PREFILL_YEAR = 1900
MAX_PREFILL_YEAR = 2100


class TextMessage(Protocol):
    @property
    def kind(self) -> str: ...
    @property
    def text(self) -> str | None: ...
    @property
    def occurred_at(self) -> Any: ...
    @property
    def sequence(self) -> int: ...


def output_schema() -> PrefillJsonSchema:
    schema = PrefillResult.model_json_schema()
    schema["required"] = list(PrefillResult.model_fields)
    for field in schema["properties"].values():
        field.pop("default", None)
    vendor_schema = schema["$defs"]["PrefillVendorInfo"]
    vendor_schema["required"] = list(vendor_schema["properties"])
    for field in vendor_schema["properties"].values():
        field.pop("default", None)
    schema["properties"]["year"]["anyOf"] = [
        {"type": "integer", "minimum": MIN_PREFILL_YEAR, "maximum": MAX_PREFILL_YEAR},
        {"type": "null"},
    ]
    return PrefillJsonSchema(json_schema=schema)


def build_input(messages: Iterable[TextMessage], brands: list[dict[str, str]],
                supplement: str, vendors: list[dict[str, str]] | None = None) -> PrefillContent:
    ordered = sorted(messages, key=lambda item: (item.occurred_at, item.sequence))
    payload = json.dumps({"messages": [
        {"occurred_at": item.occurred_at.isoformat(), "text": item.text}
        for item in ordered if item.kind == "text"
    ], "brands": brands, "vendors": vendors or [], "supplement": supplement}, ensure_ascii=False)
    if len(payload) > MAX_INPUT_CHARACTERS:
        raise ValueError("prefill input exceeds limit")
    return PrefillContent(content=payload)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def parse_prefill(content: str, brand_ids: set[str], vendor_ids: set[str]) -> PrefillResult:
    data = json.loads(content, object_pairs_hook=_unique_object)
    if not isinstance(data, dict) or set(data) != set(PrefillResult.model_fields):
        raise ValueError("prefill fields do not match schema")
    year = data["year"]
    if isinstance(year, int) and not isinstance(year, bool) and not (
        MIN_PREFILL_YEAR <= year <= MAX_PREFILL_YEAR
    ):
        data["year"] = None
    result = PrefillResult.model_validate_json(json.dumps(data), strict=True)
    if result.brand_id is not None and result.brand_id not in brand_ids:
        raise ValueError("prefill brand is not available")
    quotes = {}
    for quote in result.vendor_info:
        if quote.vendor_id not in vendor_ids:
            raise ValueError("prefill vendor is not available")
        try:
            price_quote(quote.original_amount, quote.exchange_rate)
        except LangException as error:
            raise ValueError("prefill quote is invalid") from error
        quotes[quote.vendor_id] = quote
    result.vendor_info = list(quotes.values())
    return result


def merge_prefill(current: DraftFields, proposed: DraftFields,
                  manual_fields: list[str]) -> DraftFields:
    previous = current.model_dump()
    values = proposed.model_dump(include=set(DraftFields.model_fields))
    return DraftFields.model_validate({
        key: previous[key] if key in manual_fields else value for key, value in values.items()
    })
