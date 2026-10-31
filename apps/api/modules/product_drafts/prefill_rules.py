import json
from collections.abc import Iterable
from typing import Any, Protocol

from .prefill_schema import PrefillContent, PrefillJsonSchema
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
    schema = DraftFields.model_json_schema()
    schema["required"] = list(DraftFields.model_fields)
    for field in schema["properties"].values():
        field.pop("default", None)
    schema["properties"]["year"]["anyOf"] = [
        {"type": "integer", "minimum": MIN_PREFILL_YEAR, "maximum": MAX_PREFILL_YEAR},
        {"type": "null"},
    ]
    return PrefillJsonSchema(json_schema=schema)


def build_input(messages: Iterable[TextMessage], brands: list[dict[str, str]],
                supplement: str) -> PrefillContent:
    ordered = sorted(messages, key=lambda item: (item.occurred_at, item.sequence))
    payload = json.dumps({"messages": [
        {"occurred_at": item.occurred_at.isoformat(), "text": item.text}
        for item in ordered if item.kind == "text"
    ], "brands": brands, "supplement": supplement}, ensure_ascii=False)
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


def parse_prefill(content: str, brand_ids: set[str]) -> DraftFields:
    data = json.loads(content, object_pairs_hook=_unique_object)
    if not isinstance(data, dict) or set(data) != set(DraftFields.model_fields):
        raise ValueError("prefill fields do not match schema")
    year = data["year"]
    if isinstance(year, int) and not isinstance(year, bool) and not (
        MIN_PREFILL_YEAR <= year <= MAX_PREFILL_YEAR
    ):
        data["year"] = None
    result = DraftFields.model_validate(data, strict=True)
    if result.brand_id is not None and result.brand_id not in brand_ids:
        raise ValueError("prefill brand is not available")
    return result


def merge_prefill(current: DraftFields, proposed: DraftFields,
                  manual_fields: list[str]) -> DraftFields:
    previous = current.model_dump()
    values = proposed.model_dump()
    return DraftFields.model_validate({
        key: previous[key] if key in manual_fields else value for key, value in values.items()
    })
