import json
from datetime import timedelta
from types import SimpleNamespace

import pytest

from modules.product_drafts import prefill_rules
from modules.product_drafts.schema import DraftFields
from tests.modules.product_drafts.helpers import BASE, ID


def test_parse_prefill_requires_exact_fields_and_valid_brand():
    data = DraftFields(name="手袋", brand_id=ID).model_dump()
    assert prefill_rules.parse_prefill(json.dumps(data), {ID}).name == "手袋"
    for invalid in [{**data, "quotes": []}, {"name": "手袋"},
                    {**data, "brand_id": "22222222-2222-4222-8222-222222222222"},
                    {**data, "year": "2020"}, {**data, "cost_price": True}]:
        with pytest.raises(ValueError):
            prefill_rules.parse_prefill(json.dumps(invalid), {ID})
    with pytest.raises(ValueError):
        prefill_rules.parse_prefill('```json\n{}\n```', {ID})
    with pytest.raises(ValueError):
        prefill_rules.parse_prefill(json.dumps(data)[:-1] + ',"name":"重複"}', {ID})
    assert all(value is None for value in prefill_rules.parse_prefill(
        json.dumps(DraftFields().model_dump()), set(),
    ).model_dump().values())


def test_prompt_uses_all_text_and_supplement_without_quotes():
    messages = [SimpleNamespace(kind="text", text="後到", occurred_at=BASE + timedelta(seconds=2),
                                sequence=2),
                SimpleNamespace(kind="image", text=None, occurred_at=BASE, sequence=1),
                SimpleNamespace(kind="text", text="先到\n完整原文", occurred_at=BASE, sequence=3)]
    payload = json.loads(prefill_rules.build_input(messages, [{"id": ID, "name": "品牌"}],
                                                 "底價代表成本"))
    assert [item["text"] for item in payload["messages"]] == ["先到\n完整原文", "後到"]
    assert payload["supplement"] == "底價代表成本"
    assert payload["brands"] == [{"id": ID, "name": "品牌"}]
    schema = prefill_rules.output_schema()
    assert set(schema["required"]) == set(DraftFields.model_fields)
    assert schema["additionalProperties"] is False
    assert "quotes" not in schema["properties"]


def test_prefill_preserves_manual_fields_and_clears_obsolete_values():
    before = DraftFields(name="人工名稱", color=None, model_name="舊型號", cost_price=200)
    proposed = DraftFields(name="AI 名稱", color="紅色", cost_price=300)
    result = prefill_rules.merge_prefill(before, proposed, ["name", "color"])
    assert result.name == "人工名稱" and result.color is None
    assert result.model_name is None and result.cost_price == 300


def test_prefill_input_limit_rejects_instead_of_truncating():
    with pytest.raises(ValueError):
        prefill_rules.build_input([SimpleNamespace(kind="text", text="文" * 200001,
                                                   occurred_at=BASE, sequence=1)], [], "")
