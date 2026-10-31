import json
from datetime import timedelta
from types import SimpleNamespace

import pytest

from modules.product_drafts import prefill_rules
from modules.product_drafts.prefill_prompt import BASE_PROMPT
from modules.product_drafts.prefill_schema import PrefillResult
from modules.product_drafts.schema import DraftFields
from tests.modules.product_drafts.helpers import BASE, ID


def test_parse_prefill_requires_exact_fields_and_valid_brand():
    data = PrefillResult(name="手袋", brand_id=ID).model_dump(mode="json")
    assert prefill_rules.parse_prefill(json.dumps(data), {ID}, set()).name == "手袋"
    for invalid in [{**data, "quotes": []}, {"name": "手袋"},
                    {**data, "brand_id": "22222222-2222-4222-8222-222222222222"},
                    {**data, "year": "2020"}, {**data, "cost_price": True}]:
        with pytest.raises(ValueError):
            prefill_rules.parse_prefill(json.dumps(invalid), {ID}, set())
    with pytest.raises(ValueError):
        prefill_rules.parse_prefill('```json\n{}\n```', {ID}, set())
    with pytest.raises(ValueError):
        prefill_rules.parse_prefill(json.dumps(data)[:-1] + ',"name":"重複"}', {ID}, set())
    assert all(value is None for value in prefill_rules.parse_prefill(
        json.dumps(PrefillResult().model_dump()), set(), set(),
    ).model_dump(exclude={"vendor_info"}).values())


def test_prompt_uses_all_text_supplement_and_vendor_catalog():
    messages = [SimpleNamespace(kind="text", text="後到", occurred_at=BASE + timedelta(seconds=2),
                                sequence=2),
                SimpleNamespace(kind="image", text=None, occurred_at=BASE, sequence=1),
                SimpleNamespace(kind="text", text="先到\n完整原文", occurred_at=BASE, sequence=3)]
    payload = json.loads(prefill_rules.build_input(messages, [{"id": ID, "name": "品牌"}],
                                                 "底價代表成本",
                                                 [{"id": ID, "name": "報價廠商"}]).content)
    assert [item["text"] for item in payload["messages"]] == ["先到\n完整原文", "後到"]
    assert payload["supplement"] == "底價代表成本"
    assert payload["brands"] == [{"id": ID, "name": "品牌"}]
    schema = prefill_rules.output_schema().json_schema
    assert payload["vendors"] == [{"id": ID, "name": "報價廠商"}]
    assert set(schema["required"]) == set(PrefillResult.model_fields)
    assert schema["additionalProperties"] is False
    assert "vendor_info" in schema["properties"]


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


def test_prefill_output_schema_limits_year_to_supported_range():
    year = prefill_rules.output_schema().json_schema["properties"]["year"]
    integer = next(option for option in year["anyOf"] if option["type"] == "integer")
    assert integer["minimum"] == 1900
    assert integer["maximum"] == 2100
    assert {"type": "null"} in year["anyOf"]


@pytest.mark.parametrize("year, expected", [
    (-1, None), (0, None), (1899, None), (1900, 1900), (2026, 2026),
    (2100, 2100), (2101, None), (9999, None), (10000, None), (None, None),
])
def test_parse_prefill_ignores_year_outside_supported_range(year, expected):
    data = {**PrefillResult(name="手袋", color="黑色", cost_price=30000).model_dump(), "year": year}
    result = prefill_rules.parse_prefill(json.dumps(data), set(), set())
    assert result.year == expected
    assert result.name == "手袋" and result.color == "黑色" and result.cost_price == 30000


def test_parse_prefill_validates_vendor_quotes_and_keeps_last():
    other = "22222222-2222-4222-8222-222222222222"
    data = PrefillResult(name="手袋").model_dump(mode="json")
    data["vendor_info"] = [
        {"vendor_id": ID, "original_amount": "100", "exchange_rate": "4.5"},
        {"vendor_id": other, "original_amount": "200"},
        {"vendor_id": ID, "original_amount": "120", "exchange_rate": "4.6"},
    ]
    result = prefill_rules.parse_prefill(json.dumps(data), set(), {ID, other})
    assert len(result.vendor_info) == 2
    quotes = {item.vendor_id: item for item in result.vendor_info}
    assert quotes[ID].original_amount == 120 and str(quotes[ID].exchange_rate) == "4.6"
    assert quotes[other].exchange_rate == 1
    with pytest.raises(ValueError):
        prefill_rules.parse_prefill(json.dumps(data), set(), {ID})
    for invalid in ["0", "-1", "1.0000001", "NaN"]:
        data["vendor_info"][0]["exchange_rate"] = invalid
        with pytest.raises(ValueError):
            prefill_rules.parse_prefill(json.dumps(data), set(), {ID, other})


def test_prefill_prompt_defines_vendor_rules_and_supplement_precedence():
    for prompt in [BASE_PROMPT.zh, BASE_PROMPT.en]:
        assert all(field in prompt for field in ["vendor_info", "original_amount", "exchange_rate"])
    assert "補充條件優先" in BASE_PROMPT.zh
    assert "supplements take precedence" in BASE_PROMPT.en
    assert "名稱中的字" in BASE_PROMPT.zh and "最後一筆" in BASE_PROMPT.zh
