import json
from collections.abc import Iterable
from typing import Any, Protocol

from .schema import DraftFields

MAX_INPUT_CHARACTERS = 200000


class TextMessage(Protocol):
    @property
    def kind(self) -> str: ...
    @property
    def text(self) -> str | None: ...
    @property
    def occurred_at(self) -> Any: ...
    @property
    def sequence(self) -> int: ...


def output_schema() -> dict[str, Any]:
    schema = DraftFields.model_json_schema()
    schema["required"] = list(DraftFields.model_fields)
    for field in schema["properties"].values():
        field.pop("default", None)
    return schema


def build_input(messages: Iterable[TextMessage], brands: list[dict[str, str]],
                supplement: str) -> str:
    ordered = sorted(messages, key=lambda item: (item.occurred_at, item.sequence))
    payload = json.dumps({"messages": [
        {"occurred_at": item.occurred_at.isoformat(), "text": item.text}
        for item in ordered if item.kind == "text"
    ], "brands": brands, "supplement": supplement}, ensure_ascii=False)
    if len(payload) > MAX_INPUT_CHARACTERS:
        raise ValueError("prefill input exceeds limit")
    return payload


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
