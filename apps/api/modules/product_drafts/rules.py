from shared.http.errors import LangException

from .errors import DraftError


def check_version(actual: int, expected: int | None) -> None:
    if actual != expected:
        raise LangException(409, DraftError.STALE)
