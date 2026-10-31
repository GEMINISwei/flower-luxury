from decimal import Decimal

import pytest
from pydantic import ValidationError

from modules.products.quote_rules import price_quote
from modules.products.quote_schema import QuoteCreate, QuoteUpdate
from shared.http.errors import LangException

VENDOR_ID = "11111111-1111-4111-8111-111111111111"


@pytest.mark.parametrize("amount,rate,total", [
    ("123", "1", 123), ("1.01", "1", 1), ("0.10", "4.999999", 0),
    ("0.10", "5", 1), ("100.25", "4.512345", 452),
])
def test_quote_uses_explicit_rate_and_half_up_rounding(amount, rate, total):
    result = price_quote(Decimal(amount), Decimal(rate))
    assert result.amount_twd == total and result.exchange_rate == Decimal(rate)


@pytest.mark.parametrize("amount", ["0", "-1", "1.001", "NaN", "Infinity", "10000000000"])
def test_quote_rejects_invalid_amount(amount):
    with pytest.raises(LangException):
        price_quote(Decimal(amount), Decimal(1))


@pytest.mark.parametrize("rate", ["0", "-1", "NaN", "Infinity", "1.0000001", "10000000000"])
def test_quote_rejects_invalid_rate(rate):
    with pytest.raises((LangException, ValidationError)):
        price_quote(Decimal(100), Decimal(rate))
    with pytest.raises(ValidationError):
        QuoteCreate(vendor_id=VENDOR_ID, original_amount="100", exchange_rate=rate)


def test_quote_rejects_unsafe_converted_amount_and_defaults_rate():
    with pytest.raises(LangException):
        price_quote(Decimal("9999999999.99"), Decimal("9999999999.999999"))
    assert price_quote(Decimal("100")).amount_twd == 100
    assert QuoteCreate(vendor_id=VENDOR_ID, original_amount="100").exchange_rate == 1


@pytest.mark.parametrize("amount", ["0", "-1", "NaN", "Infinity", "1.001"])
def test_quote_schema_rejects_invalid_amounts(amount):
    with pytest.raises(ValidationError):
        QuoteCreate(vendor_id=VENDOR_ID, original_amount=amount)


def test_quote_schema_accepts_rate_but_ignores_computed_amounts():
    form = QuoteCreate.model_validate({
        "vendor_id": VENDOR_ID, "original_amount": "100.25", "exchange_rate": "4.5",
        "currency": "TWD", "amount_twd": 1, "has_sales": False,
    })
    assert form.model_dump() == {"vendor_id": VENDOR_ID, "original_amount": Decimal("100.25"),
                                 "exchange_rate": Decimal("4.5"), "note": None}
    assert QuoteUpdate(original_amount="100", exchange_rate="2").exchange_rate == 2
