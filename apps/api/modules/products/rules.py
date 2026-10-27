from shared.http.errors import LangException

from .errors import ProductError


def ensure_editable(status: str) -> None:
    if status == "sold":
        raise LangException(409, ProductError.SOLD_LOCKED)


def ensure_transition(source: str, target: str, *, returning: bool = False) -> None:
    # 售出必須經詢價成交, 這個入口只允許帶原因的退回.
    if not (returning and source == "sold" and target == "not_acquired"):
        raise LangException(409, ProductError.INVALID_TRANSITION)
