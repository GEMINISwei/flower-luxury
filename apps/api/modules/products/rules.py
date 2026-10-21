from shared.http.errors import BaseError, LangException, LangText


class ProductError(BaseError):
    NOT_FOUND = LangText(zh="商品不存在", en="Product not found")
    SOLD_LOCKED = LangText(
        zh="已出售商品已鎖定，請先退回", en="Sold product is locked; return it first",
    )
    INVALID_TRANSITION = LangText(zh="不允許此狀態轉換", en="This status transition is not allowed")
    PHOTO_NOT_FOUND = LangText(zh="照片不存在", en="Photo not found")


def ensure_transition(source: str, target: str, *, returning: bool = False) -> None:
    # 售出必須經詢價成交, 這個入口只允許帶原因的退回.
    if not (returning and source == "sold" and target == "not_acquired"):
        raise LangException(409, ProductError.INVALID_TRANSITION)


def ensure_editable(status: str) -> None:
    if status == "sold":
        raise LangException(409, ProductError.SOLD_LOCKED)
