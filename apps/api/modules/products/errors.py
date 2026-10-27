from shared.http.errors import BaseError, LangText


class ProductError(BaseError):
    NOT_FOUND = LangText(zh="商品不存在", en="Product not found")
    SOLD_LOCKED = LangText(
        zh="已出售商品已鎖定，請先退回", en="Sold product is locked; return it first",
    )
