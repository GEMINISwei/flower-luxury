from shared.http.errors import BaseError, LangException, LangText


class ProductError(BaseError):
    NOT_FOUND = LangText(zh="商品不存在", en="Product not found")
    SOLD_LOCKED = LangText(
        zh="已售出商品已鎖定，請先退回", en="Sold product is locked; return it first",
    )
    INVALID_TRANSITION = LangText(zh="不允許此狀態轉換", en="This status transition is not allowed")
    PHOTO_NOT_FOUND = LangText(zh="照片不存在", en="Photo not found")


FORWARD = {"not_acquired": {"in_stock"}, "in_stock": set(), "sold": set()}
RETURNS = {"not_acquired": set(), "in_stock": {"not_acquired"},
           "sold": {"in_stock", "not_acquired"}}


def ensure_transition(source: str, target: str, *, returning: bool = False) -> None:
    transitions = RETURNS if returning else FORWARD
    if target not in transitions.get(source, set()):
        raise LangException(409, ProductError.INVALID_TRANSITION)


def ensure_editable(status: str) -> None:
    if status == "sold":
        raise LangException(409, ProductError.SOLD_LOCKED)
