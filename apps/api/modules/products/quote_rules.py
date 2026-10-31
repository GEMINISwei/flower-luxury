from decimal import ROUND_HALF_UP, Decimal

from shared.http.errors import LangException

from .errors import QuoteError
from .quote_schema import QuoteAmounts


def price_quote(amount: Decimal, rate: Decimal = Decimal(1)) -> QuoteAmounts:
    if (not amount.is_finite() or amount <= 0 or amount > Decimal("9999999999.99")
            or amount != amount.quantize(Decimal("0.01"))):
        raise LangException(422, QuoteError.AMOUNT)
    if (not rate.is_finite() or rate <= 0 or rate > Decimal("9999999999.999999")
            or rate != rate.quantize(Decimal("0.000001"))):
        raise LangException(422, QuoteError.RATE)
    total = int((amount * rate).quantize(Decimal(1), rounding=ROUND_HALF_UP))
    if total > 9007199254740991:
        raise LangException(422, QuoteError.AMOUNT)
    return QuoteAmounts(exchange_rate=rate, amount_twd=total)
