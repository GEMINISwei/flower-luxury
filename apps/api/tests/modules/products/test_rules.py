from datetime import datetime

import pytest
from pydantic import ValidationError

from modules.products import model
from modules.products.schema import ProductCreate

FORM = {"name": "手袋", "brand_id": "11111111-1111-4111-8111-111111111111",
        "category": "包包", "cost_price": 3000}


@pytest.mark.parametrize("field,value", [
    ("name", "  "), ("brand_id", "bad"), ("category", "未知"),
    ("cost_price", -1), ("cost_price", 1.5), ("cost_price", 2147483648),
    ("year", 0), ("year", 10000),
])
def test_product_form_rejects_invalid_fields(field, value):
    with pytest.raises(ValidationError):
        ProductCreate.model_validate({**FORM, field: value})


def test_create_ignores_injected_workflow_fields():
    form = ProductCreate.model_validate({
        **FORM, "status": "sold", "sku": "injected", "main_photo_id": "injected",
        "created_by": "injected", "deleted_at": "2026-10-27T00:00:00Z",
    })
    for field in ["status", "sku", "main_photo_id", "created_by", "deleted_at"]:
        assert field not in form.model_dump()


def test_sku_uses_taipei_date(monkeypatch):
    monkeypatch.setattr(model, "utc_now", lambda: datetime(2026, 10, 27, 16, 1))
    monkeypatch.setattr(model.secrets, "choice", lambda _alphabet: "A")
    assert model.generate_sku() == "LX20261028AAAAA"
