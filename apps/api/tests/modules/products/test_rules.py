import pytest
from pydantic import ValidationError

from modules.products.rules import ensure_transition
from modules.products.schema import ProductCreate, StatusChange, StatusReturn
from shared.http.errors import LangException

FORM = {"name": "手袋", "brand_id": "11111111-1111-4111-8111-111111111111",
        "category": "包包", "cost_price": 3000}


@pytest.mark.parametrize("source,target,returning,allowed", [
    ("not_acquired", "sold", False, False), ("sold", "not_acquired", False, False),
    ("sold", "not_acquired", True, True), ("not_acquired", "not_acquired", True, False),
    ("sold", "sold", True, False), ("not_acquired", "in_stock", False, False),
    ("sold", "in_stock", True, False), ("in_stock", "not_acquired", True, False),
])
def test_status_transitions_follow_workflow(source, target, returning, allowed):
    if allowed:
        ensure_transition(source, target, returning=returning)
    else:
        with pytest.raises(LangException) as error:
            ensure_transition(source, target, returning=returning)
        assert error.value.status_code == 409


@pytest.mark.parametrize("reason", ["", "   ", None])
def test_return_requires_reason(reason):
    with pytest.raises(ValidationError):
        StatusReturn(to_status="not_acquired", reason=reason)
    assert StatusChange(to_status="sold").reason is None


@pytest.mark.parametrize("field,value", [
    ("name", "  "), ("brand_id", "bad"), ("category", "未知"),
    ("cost_price", -1), ("cost_price", 1.5), ("year", 0), ("year", 10000),
])
def test_product_form_rejects_invalid_fields(field, value):
    with pytest.raises(ValidationError):
        ProductCreate.model_validate({**FORM, field: value})


def test_create_ignores_injected_workflow_fields():
    form = ProductCreate.model_validate({**FORM, "status": "sold", "sku": "injected"})
    assert "status" not in form.model_dump()
    assert "sku" not in form.model_dump()
    assert form.name == "手袋"


@pytest.mark.parametrize("model", [StatusChange, StatusReturn])
def test_status_payload_rejects_removed_in_stock(model):
    with pytest.raises(ValidationError):
        model(to_status="in_stock", reason="legacy")
