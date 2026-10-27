from decimal import ROUND_HALF_UP, Decimal

from shared.http.errors import LangException

from .errors import QuoteError
from .quote_schema import QuoteAmounts


def price_quote(country: str, amount: Decimal, rate: Decimal | None) -> QuoteAmounts:
    if (not amount.is_finite() or amount <= 0 or amount > Decimal("9999999999.99")
            or amount != amount.quantize(Decimal("0.01"))):
        raise LangException(422, QuoteError.AMOUNT)
    if country == "TW":
        if amount != amount.to_integral_value():
            raise LangException(422, QuoteError.AMOUNT)
        return QuoteAmounts(currency="TWD", exchange_rate=Decimal(1), amount_twd=int(amount))
    if rate is None or not rate.is_finite() or rate <= 0:
        raise LangException(409, QuoteError.NO_RATE)
    total = int((amount * rate).quantize(Decimal(1), rounding=ROUND_HALF_UP))
    if total > 9007199254740991:
        raise LangException(422, QuoteError.AMOUNT)
    return QuoteAmounts(currency="CNY", exchange_rate=rate, amount_twd=total)
