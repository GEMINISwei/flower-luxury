from decimal import Decimal

import pytest
from pydantic import ValidationError

from modules.products.quote_rules import price_quote
from modules.products.quote_schema import QuoteCreate, QuoteUpdate
from shared.http.errors import LangException

VENDOR_ID = "11111111-1111-4111-8111-111111111111"


@pytest.mark.parametrize("country,amount,rate,currency,total", [
    ("TW", "123", "4.512345", "TWD", 123),
    ("CN", "0.10", "4.999999", "CNY", 0),
    ("CN", "0.10", "5", "CNY", 1),
    ("CN", "100.25", "4.512345", "CNY", 452),
])
def test_quote_uses_country_currency_and_half_up_rounding(country, amount, rate, currency, total):
    result = price_quote(country, Decimal(amount), Decimal(rate))
    assert result.currency == currency
    assert result.amount_twd == total
    assert result.exchange_rate == (Decimal(1) if country == "TW" else Decimal(rate))


@pytest.mark.parametrize("country,amount", [
    ("TW", "1.01"), ("CN", "0"), ("TW", "-1"), ("CN", "1.001"),
    ("CN", "NaN"), ("CN", "Infinity"), ("CN", "10000000000"),
])
def test_quote_amount_validation_follows_country(country, amount):
    with pytest.raises(LangException):
        price_quote(country, Decimal(amount), Decimal("4.5"))


def test_cny_quote_requires_rate_and_rejects_unsafe_amount():
    with pytest.raises(LangException) as error:
        price_quote("CN", Decimal("100"), None)
    assert error.value.status_code == 409
    with pytest.raises(LangException):
        price_quote("CN", Decimal("9999999999.99"), Decimal("9999999999.999999"))
    assert price_quote("TW", Decimal("1"), None).amount_twd == 1


@pytest.mark.parametrize("amount", ["0", "-1", "NaN", "Infinity", "1.001"])
def test_quote_schema_rejects_invalid_amounts(amount):
    with pytest.raises(ValidationError):
        QuoteCreate(vendor_id=VENDOR_ID, original_amount=amount)


def test_quote_ignores_injected_currency_and_rate():
    form = QuoteCreate.model_validate({
        "vendor_id": VENDOR_ID, "original_amount": "100.25", "currency": "TWD",
        "exchange_rate": "1", "amount_twd": 1, "has_sales": False,
    })
    assert form.model_dump() == {
        "vendor_id": VENDOR_ID, "original_amount": Decimal("100.25"), "note": None,
    }
    assert "exchange_rate" not in QuoteUpdate.model_validate({
        "original_amount": "100", "note": "new", "exchange_rate": "99",
    }).model_dump()
