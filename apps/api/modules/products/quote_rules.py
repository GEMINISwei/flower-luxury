from decimal import ROUND_HALF_UP, Decimal

from shared.http.errors import BaseError, LangException, LangText

from .quote_schema import QuoteAmounts


class QuoteError(BaseError):
    NOT_FOUND = LangText(zh="詢價不存在或不屬於此商品", en="Quote not found for this product")
    DUPLICATE = LangText(
        zh="此廠商已有詢價，請修改既有報價", en="This vendor already has a quote; edit it instead",
    )
    AMOUNT = LangText(
        zh="報價須大於零；臺幣為整數，人民幣最多兩位小數，且金額不可超出範圍",
        en="Quote must be positive: whole TWD or up to two CNY decimals, within the amount limit",
    )
    NO_RATE = LangText(zh="請先由店長設定人民幣匯率", en="Ask a manager to set the CNY rate first")
    REFERENCED = LangText(
        zh="曾用於成交的詢價不能刪除", en="A previously sold quote cannot be deleted",
    )
    STALE = LangText(
        zh="報價或成本已變動，請重新載入後確認成交",
        en="Quote or cost changed; reload before confirming the sale",
    )


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
