from shared.http.errors import LangException

from .errors import ProductError


def ensure_editable(status: str) -> None:
    if status == "sold":
        raise LangException(409, ProductError.SOLD_LOCKED)
